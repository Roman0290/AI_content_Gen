"""Smoke test: call each provider once, save a tiny output, log latency to runs.jsonl.

    python scripts/smoke_test.py               # run all checks
    python scripts/smoke_test.py --only tts    # one check: text, tts, image, kaggle, ffmpeg
    python scripts/smoke_test.py --list-models # print Gemini model IDs your key can see

Each check is independent: one failing provider does not stop the others.
"""
import argparse
import base64
import os
import shutil
import subprocess
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import requests  # noqa: E402

from pipeline.common.config import OUTPUTS, env  # noqa: E402
from pipeline.common.logging import timed_call  # noqa: E402
from pipeline.common.gemini import TEXT_FALLBACK, TEXT_MODEL, TTS_MODEL, client  # noqa: E402
from pipeline.common.retry import with_retry  # noqa: E402

SMOKE_DIR = OUTPUTS / "smoke"

CF_MODEL = os.getenv("CF_IMAGE_MODEL", "@cf/black-forest-labs/flux-1-schnell")

# A line from the film itself, so the TTS check also tests Amharic pronunciation.
AMHARIC_LINE = "እኔ መጥቼ ካገኘሁት... እረግጥሻለሁ!"


def gemini_client():
    return client()


def list_models() -> None:
    client = gemini_client()  # keep a reference: the pager needs the client open while iterating
    for m in client.models.list():
        print(m.name, getattr(m, "supported_actions", ""))


def check_text() -> str:
    client = gemini_client()
    prompt = "Translate to English in one short line: ራሴ ላይ አድርጊው!"
    last = None
    for model in (TEXT_MODEL, TEXT_FALLBACK):  # fall back when the primary is overloaded
        try:
            with timed_call("smoke", model, {"prompt": prompt}) as rec:
                resp = with_retry(client.models.generate_content)(model=model, contents=prompt)
                text = (resp.text or "").strip()
                usage = resp.usage_metadata
                rec["tokens_in"] = getattr(usage, "prompt_token_count", None)
                rec["tokens_out"] = getattr(usage, "candidates_token_count", None)
                rec["output"] = text
            return f"[{model}] {text}"
        except Exception as e:
            last = e
            print(f"       {model} failed ({type(e).__name__}), trying fallback...")
    raise last


def check_tts() -> str:
    from google.genai import types

    client = gemini_client()
    voice = "Kore"
    prompt = f"Say it like an impatient but loving Ethiopian mother calling from another room: {AMHARIC_LINE}"
    out = SMOKE_DIR / "tts_amharic.wav"
    with timed_call("smoke", TTS_MODEL, {"voice": voice, "text": AMHARIC_LINE}) as rec:
        resp = with_retry(client.models.generate_content)(
            model=TTS_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                    )
                ),
            ),
        )
        pcm = resp.candidates[0].content.parts[0].inline_data.data
        with wave.open(str(out), "wb") as w:  # Gemini TTS returns 24 kHz 16-bit mono PCM
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(24000)
            w.writeframes(pcm)
        rec["output"] = str(out.relative_to(ROOT))
        rec["audio_s"] = round(len(pcm) / (24000 * 2), 2)
    return f"{out.relative_to(ROOT)} ({rec['audio_s']}s of audio)"


def _post(url, **kw):
    r = requests.post(url, **kw)
    r.raise_for_status()
    return r


def check_image() -> str:
    account, token = env("CF_ACCOUNT_ID"), env("CF_API_TOKEN")
    prompt = (
        "Warm hand-painted illustration of an Ethiopian living room, jebena coffee pot "
        "on a low table, golden afternoon light, soft grain"
    )
    params = {"prompt": prompt, "steps": 4}  # flux-1-schnell on Workers AI rejects a seed parameter
    out = SMOKE_DIR / "image_flux.jpg"
    url = f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{CF_MODEL}"
    with timed_call("smoke", CF_MODEL, params) as rec:
        r = with_retry(_post)(url, headers={"Authorization": f"Bearer {token}"}, json=params, timeout=120)
        out.write_bytes(base64.b64decode(r.json()["result"]["image"]))
        rec["output"] = str(out.relative_to(ROOT))
    return str(out.relative_to(ROOT))


def check_kaggle() -> str:
    user, key = env("KAGGLE_USERNAME"), env("KAGGLE_KEY")
    # New Kaggle API tokens (KGAT_...) use Bearer auth; legacy kaggle.json keys use basic auth.
    kwargs = {"headers": {"Authorization": f"Bearer {key}"}} if key.startswith("KGAT_") else {"auth": (user, key)}
    with timed_call("smoke", "kaggle-api", {"endpoint": "kernels/list"}) as rec:
        r = requests.get(
            "https://www.kaggle.com/api/v1/kernels/list",
            params={"page": 1, "pageSize": 1, "user": user},
            timeout=30,
            **kwargs,
        )
        r.raise_for_status()
        rec["output"] = "authenticated"
    return "authenticated (GPU quota and phone verification: check kaggle.com -> Settings)"


def check_ffmpeg() -> str:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg not found on PATH")
    first = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True).stdout.splitlines()[0]
    return first


CHECKS = {
    "text": ("Gemini text", check_text),
    "tts": ("Gemini TTS (Amharic)", check_tts),
    "image": ("Cloudflare FLUX", check_image),
    "kaggle": ("Kaggle API", check_kaggle),
    "ffmpeg": ("FFmpeg (local)", check_ffmpeg),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=CHECKS)
    ap.add_argument("--list-models", action="store_true")
    args = ap.parse_args()

    if args.list_models:
        list_models()
        return

    SMOKE_DIR.mkdir(parents=True, exist_ok=True)
    failed = 0
    for key, (label, fn) in CHECKS.items():
        if args.only and key != args.only:
            continue
        try:
            print(f"[ OK ] {label}: {fn()}")
        except Exception as e:  # report and keep going
            failed += 1
            msg = str(e).splitlines()[0][:200]
            print(f"[FAIL] {label}: {type(e).__name__}: {msg}")
            if key in ("text", "tts") and "404" in str(e):
                print("       Model ID not found. Run with --list-models and set it in .env.")
    print(f"\n{failed} failed. Every call is logged in runs.jsonl.")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
