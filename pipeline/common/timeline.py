"""The film's timeline: where each shot and each narration line sits, computed from the storyboard
and the narration manifest. Subtitles and assembly both use it, so they can never disagree."""
import json

from .config import OUTPUTS, ROOT

LEAD_S = 0.3  # the line starts this long after the cut


def build(sb: dict) -> dict:
    manifest_path = OUTPUTS / "narration" / "manifest.json"
    narr = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    shots, t = [], 0.0
    for shot in sb["shots"]:
        n = narr.get(shot["id"])
        dur = n["fitted_s"] if n else shot["duration_s"]
        entry = {"id": shot["id"], "start": round(t, 3), "dur": dur, "subtitle_en": shot["subtitle_en"]}
        if n:
            entry.update(clip=str(ROOT / n["file"]), line_start=round(t + LEAD_S, 3),
                         line_end=round(t + LEAD_S + n["audio_s"], 3))
        shots.append(entry)
        t += dur
    card = sb.get("end_card_duration_s", 3)
    return {"shots": shots, "end_card": {"start": round(t, 3), "dur": card, "text": sb.get("end_card", "Made with AI")},
            "total": round(t + card, 3)}
