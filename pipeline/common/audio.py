"""Small FFmpeg helpers for audio."""
import json
import subprocess
from pathlib import Path


def duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    return round(float(json.loads(out)["format"]["duration"]), 3)


def trim_silence(src: Path, dst: Path, threshold_db: int = -45) -> None:
    """Remove leading and trailing silence (keeps pauses inside the line)."""
    trim = f"silenceremove=start_periods=1:start_threshold={threshold_db}dB:start_silence=0.05"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(src), "-af", f"{trim},areverse,{trim},areverse", str(dst)],
        check=True,
    )
