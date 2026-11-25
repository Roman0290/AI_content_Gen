"""One-off repair for F09: narration clips made before the fix contain a WAV header (start click) and a
provenance metadata chunk (end noise burst) decoded as audio. The real audio is still inside, byte for
byte, so extract the embedded WAV, re-trim silence and update the manifest. No new TTS calls."""
import io
import json
import sys
import tempfile
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.common.audio import duration, trim_silence  # noqa: E402
from pipeline.common.gemini import write_wav  # noqa: E402
from pipeline.narration import MANIFEST, PAD_S  # noqa: E402
from pipeline.common.config import load_storyboard  # noqa: E402

planned = {s["id"]: s["duration_s"] for s in load_storyboard()["shots"]}
manifest = json.loads(MANIFEST.read_text())
for sid, m in manifest.items():
    path = ROOT / m["file"]
    with wave.open(str(path)) as w:
        data = w.readframes(w.getnframes())
    start = data.find(b"RIFF")
    if start < 0:
        print(f"{sid}: already clean")
        continue
    with wave.open(io.BytesIO(data[start:])) as inner:
        pcm, rate = inner.readframes(inner.getnframes()), inner.getframerate()
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        write_wav(Path(tmp.name), pcm, rate)
        trim_silence(Path(tmp.name), path)
    old = m["audio_s"]
    m["audio_s"] = duration(path)
    m["fitted_s"] = round(max(planned[sid], m["audio_s"] + PAD_S), 2)
    m["repaired"] = "F09"
    print(f"{sid}: {old:.2f}s -> {m['audio_s']:.2f}s (header at byte {start})")
MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
