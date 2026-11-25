"""E03: do short emotion tags ("[angry] line") change Mom's delivery without being read aloud?
Runs on a model with spare quota (default gemini-3.1-flash-tts-preview) so the main model's
daily quota is saved for the film. Writes outputs/experiments/tts_emotion/."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pipeline.common.audio import duration, trim_silence  # noqa: E402
from pipeline.common.config import load_storyboard  # noqa: E402
from pipeline.common.gemini import tts_pcm, write_wav  # noqa: E402
from pipeline.common.logging import timed_call  # noqa: E402
from pipeline.common.retry import with_retry  # noqa: E402

MODEL = sys.argv[1] if len(sys.argv) > 1 else "gemini-3.1-flash-tts-preview"
OUT = ROOT / "outputs" / "experiments" / "tts_emotion"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sb = load_storyboard()
    for shot in [s for s in sb["shots"] if s["id"] in ("shot_05", "shot_07", "shot_11")]:
        voice = sb["voices"][shot["speaker"]]
        for label, text in (("plain", shot["narration"]), ("tagged", f"[{shot['tts_tag']}] {shot['narration']}")):
            out = OUT / f"{shot['id']}_{label}_{MODEL}.wav"
            raw = out.with_suffix(".raw.wav")
            try:
                with timed_call("exp_tts_emotion", MODEL, {"shot": shot["id"], "voice": voice, "text": text}) as rec:
                    write_wav(raw, with_retry(tts_pcm)(text, voice, MODEL))
                    trim_silence(raw, out)
                    raw.unlink()
                    rec["audio_s"] = duration(out)
                print(f"{shot['id']} {label:<6} {rec['audio_s']:5.2f}s  {out.relative_to(ROOT)}")
            except Exception as e:
                print(f"{shot['id']} {label:<6} FAILED {str(e)[:140]}")


if __name__ == "__main__":
    main()
