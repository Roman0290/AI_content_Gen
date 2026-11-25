"""Stage 4: narration. One Gemini TTS clip per shot, in the shot speaker's voice.

Reads  storyboard.json  (shots[].narration, shots[].speaker, voices)
Writes outputs/narration/<shot>_<hash>.wav   trimmed clip, cached by hash of (model, voice, text)
       outputs/narration/manifest.json      clip path, audio length and fitted shot length per shot

A shot is re-generated only when its text, voice or model changes. Shots whose line is longer than
the planned duration are stretched to fit (audio + padding); the total is checked against 60-90 s.

    python -m pipeline.narration                # all shots, using the cache
    python -m pipeline.narration --shot shot_05 # one shot
    python -m pipeline.narration --force        # ignore the cache
    python -m pipeline.narration --allow-fallback  # use the lite TTS model if the main one is out of quota

By default only the main TTS model is used: the lite model sounded unnatural to native listeners
(user feedback, E03), so a clip made by any other model is treated as stale and regenerated.
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path

from pipeline.common.audio import duration, trim_silence
from pipeline.common.cache import cached_path, input_hash, is_cached
from pipeline.common.config import OUTPUTS, ROOT, load_storyboard
from pipeline.common.gemini import (TTS_FALLBACK, TTS_MODEL, key_index, next_key, split_wav, tts_wav_bytes,
                                    write_wav)
from pipeline.common.logging import timed_call
from pipeline.common.retry import is_daily_quota, with_retry

OUT = OUTPUTS / "narration"
MANIFEST = OUT / "manifest.json"
EXHAUSTED: set = set()  # models whose daily quota ran out during this run; skipped for later shots
PAD_S = 0.6  # breathing room after a line before the cut
MIN_TOTAL, MAX_TOTAL = 60, 90


def tts_text(shot: dict) -> str:
    """What is actually spoken: an optional short emotion tag, then the Amharic line."""
    tag = shot.get("tts_tag")
    return f"[{tag}] {shot['narration']}" if tag else shot["narration"]


def generate(shot: dict, voice: str, out: Path, allow_fallback: bool) -> str:
    """Call TTS with retries; optionally fall back to the lite TTS model."""
    last = None
    text = tts_text(shot)
    for model in (TTS_MODEL, TTS_FALLBACK) if allow_fallback else (TTS_MODEL,):
        while model not in EXHAUSTED:
            try:
                with timed_call("narration", model, {"shot": shot["id"], "voice": voice, "text": text,
                                                     "key": key_index()}) as rec:
                    data = with_retry(tts_wav_bytes)(text, voice, model)
                    out.with_suffix(".source.wav").write_bytes(data)  # untouched response, provenance metadata kept
                    pcm, rate = split_wav(data)
                    with tempfile.NamedTemporaryFile(suffix=".wav") as raw:
                        write_wav(Path(raw.name), pcm, rate)
                        trim_silence(Path(raw.name), out)
                    rec["audio_s"] = duration(out)
                    rec["output"] = str(out.relative_to(ROOT))
                return model
            except Exception as e:
                last = e
                print(f"  {shot['id']}: {model} key#{key_index()} failed ({type(e).__name__}: {str(e)[:120]})",
                      file=sys.stderr)
                if not is_daily_quota(e):
                    break
                if next_key():  # same model, next project's key
                    print(f"  switching to API key #{key_index()}", file=sys.stderr)
                    continue
                EXHAUSTED.add(model)
    raise last or RuntimeError("all TTS models have exhausted their daily quota")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shot", help="only this shot id, e.g. shot_05")
    ap.add_argument("--force", action="store_true", help="regenerate even if cached")
    ap.add_argument("--allow-fallback", action="store_true", help="use the lite TTS model if the main one fails")
    args = ap.parse_args()

    sb = load_storyboard()
    voices = sb["voices"]
    old = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    manifest, made, failed = {}, 0, []

    for shot in sb["shots"]:
        sid, voice = shot["id"], voices[shot["speaker"]]
        # The primary model id is part of the hash so a model change regenerates; a fallback clip is
        # kept under the same key and recorded in the manifest.
        h = input_hash("narration-v1", TTS_MODEL, voice, tts_text(shot))
        out = cached_path(OUT, sid, h, "wav")
        selected = args.shot in (None, sid)
        prev = old.get(sid, {})
        made_by_fallback = prev.get("hash") == h and prev.get("model") not in (None, TTS_MODEL)
        stale = made_by_fallback and not args.allow_fallback

        if selected and (args.force or stale or not is_cached(out)):
            try:
                model = generate(shot, voice, out, args.allow_fallback)
                made += 1
                status = "new"
            except Exception:
                failed.append(sid)
                if prev and (ROOT / prev["file"]).exists():  # keep the previous clip so the radio cut still plays
                    manifest[sid] = {**prev, "stale": True}
                continue
        elif is_cached(out):
            model = prev.get("model", TTS_MODEL)
            status = "cached"
        else:
            failed.append(sid)
            continue

        audio_s = duration(out)
        fitted = round(max(shot["duration_s"], audio_s + PAD_S), 2)
        manifest[sid] = {
            "file": str(out.relative_to(ROOT)), "hash": h, "model": model, "speaker": shot["speaker"],
            "voice": voice, "audio_s": audio_s, "planned_s": shot["duration_s"], "fitted_s": fitted,
        }
        flag = "  <- longer than planned" if fitted > shot["duration_s"] else ""
        print(f"{sid} [{status:>6}] {shot['speaker']:<8} {voice:<8} audio {audio_s:5.2f}s  shot {fitted:5.2f}s{flag}")

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    total = round(sum(m["fitted_s"] for m in manifest.values()) + sb.get("end_card_duration_s", 0), 2)
    kept = sum(1 for m in manifest.values() if m.get("stale"))
    print(f"\n{made} generated, {len(manifest) - made - kept} from cache, {len(failed)} failed "
          f"({kept} of those keep their previous clip as a placeholder). "
          f"Film length with end card: {total}s (target {MIN_TOTAL}-{MAX_TOTAL}s).")
    if failed:
        print(f"Failed shots: {', '.join(failed)}. Re-run to retry; cached shots are not regenerated.")
    if not MIN_TOTAL <= total <= MAX_TOTAL:
        print("WARNING: film length is outside the target; shorten lines or shot durations.")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
