"""E06: a tester said Mom's first line mispronounces the ejective ch' (ጨ-family) in "አምጪልኝ" (shot_02).
Three takes, same voice (Kore): A retake of the same line, B with a [clear] tag, C a rephrase without the sound.
Outputs go to outputs/experiments/e06_ch_sound/ for a native listener to choose from; nothing in the film changes."""
import sys
from pathlib import Path

from pipeline.common import gemini
from pipeline.common.logging import timed_call
from pipeline.common.retry import is_daily_quota

OUT = Path("outputs/experiments/e06_ch_sound")
TAKES = {
    "A_retake": "ልጄ፣ ቦርሳዬን ከመኝታ ቤቱ ጠረጴዛ ላይ አምጪልኝ።",
    "B_clear_tag": "[clear, careful pronunciation] ልጄ፣ ቦርሳዬን ከመኝታ ቤቱ ጠረጴዛ ላይ አምጪልኝ።",
    "C_rephrase": "ልጄ፣ ቦርሳዬን ከመኝታ ቤቱ ጠረጴዛ ላይ ይዘሽልኝ ነይ።",
}
only = sys.argv[1:] or list(TAKES)
for name in only:
    text = TAKES[name]
    while True:
        try:
            with timed_call("experiment_e06", gemini.TTS_MODEL, {"take": name, "voice": "Kore", "text": text,
                                                                 "key_index": gemini.key_index()}, None, 0.0):
                data = gemini.tts_wav_bytes(text, "Kore")
            pcm, rate = gemini.split_wav(data)
            gemini.write_wav(OUT / f"{name}.wav", pcm, rate)
            print(name, "ok", OUT / f"{name}.wav")
            break
        except Exception as e:
            if is_daily_quota(e) and gemini.next_key():
                continue
            print(name, "FAILED:", "daily quota" if is_daily_quota(e) else repr(e)[:200])
            sys.exit(1)
