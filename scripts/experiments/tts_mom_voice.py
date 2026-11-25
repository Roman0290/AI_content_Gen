"""E02: make Mom sound like a real Habesha mom. Same line, different voices and direction.
Writes outputs/experiments/tts_mom/<variant>.wav and logs each call; prints duration and pause time."""
import subprocess
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from google.genai import types  # noqa: E402

from pipeline.common.logging import timed_call  # noqa: E402
from pipeline.common.retry import with_retry  # noqa: E402
from scripts.smoke_test import TTS_MODEL, gemini_client  # noqa: E402

OUT = ROOT / "outputs" / "experiments" / "tts_mom"
LINE = "እኔ መጥቼ ካገኘሁት እረግጥሻለሁ!"  # no ellipsis: "…" makes the model insert a long pause

SCENE = (
    "You are an Ethiopian mother from Addis Ababa in your forties, sitting with guests at a coffee ceremony. "
    "Your daughter just shouted from the bedroom that she can't find your bag. You are not really angry: "
    "half joking, half warning, the way every Habesha mom says it, a little louder so she hears you in the "
    "other room. Natural conversational Amharic, normal speed, no dramatic pauses, not like a newsreader."
)
SCENE_AM = (
    "እንደ አዲስ አበባ እናት ተናገሪ። ልጅሽ ከመኝታ ቤት ቦርሳሽን አላገኘሁትም ብላ ጮኸች። "
    "በግማሽ ቀልድ በግማሽ ማስጠንቀቂያ፣ በተፈጥሮ የንግግር ፍጥነት፣ ያለ ረጅም ፋታ ተናገሪ።"
)

SHORT = "Say it like a half-joking, half-warning Ethiopian mom calling to the next room"

# (voice, direction, where the direction goes). Round 1 put long directions in the prompt and the
# model read them aloud (17-29 s clips), so round 2 tests a system instruction and a short prefix.
VARIANTS = {
    "E_kore_system": ("Kore", SCENE, "system"),
    "F_sulafat_system": ("Sulafat", SCENE, "system"),
    "G_gacrux_system": ("Gacrux", SCENE, "system"),
    "H_kore_short_prefix": ("Kore", SHORT, "prefix"),
    "I_sulafat_short_prefix": ("Sulafat", SHORT, "prefix"),
}


def pause_seconds(path: Path) -> float:
    err = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(path), "-af", "silencedetect=n=-40dB:d=0.3", "-f", "null", "-"],
        capture_output=True, text=True,
    ).stderr
    return round(sum(float(l.split("silence_duration: ")[1]) for l in err.splitlines() if "silence_duration" in l), 2)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    client = gemini_client()
    for name, (voice, direction, where) in VARIANTS.items():
        out = OUT / f"{name}.wav"
        try:
            with timed_call("exp_tts_mom", TTS_MODEL, {"voice": voice, "direction": direction, "where": where, "text": LINE}) as rec:
                resp = with_retry(client.models.generate_content)(
                    model=TTS_MODEL,
                    contents=LINE if where == "system" else f"{direction}: {LINE}",
                    config=types.GenerateContentConfig(
                        system_instruction=direction if where == "system" else None,
                        response_modalities=["AUDIO"],
                        speech_config=types.SpeechConfig(
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                            )
                        ),
                    ),
                )
                pcm = resp.candidates[0].content.parts[0].inline_data.data
                with wave.open(str(out), "wb") as w:
                    w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(pcm)
                rec["audio_s"] = round(len(pcm) / 48000, 2)
                rec["pause_s"] = pause_seconds(out)
                rec["output"] = str(out.relative_to(ROOT))
            print(f"{name:<28} {voice:<8} audio {rec['audio_s']:>5}s  pauses {rec['pause_s']:>4}s  -> {rec['output']}")
        except Exception as e:
            print(f"{name:<28} FAILED {type(e).__name__}: {str(e)[:150]}")


if __name__ == "__main__":
    main()
