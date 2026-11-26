"""Content-addressed cache: an output is reused when the hash of its inputs is unchanged."""
import hashlib
import json
from pathlib import Path


def input_hash(*parts) -> str:
    blob = json.dumps(parts, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:12]


def cached_path(out_dir: Path, shot_id: str, h: str, ext: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / f"{shot_id}_{h}.{ext}"


def is_cached(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


def wan_name(shot: dict, keyframe_hash: str) -> str:
    """File stem of a shot's Wan clip. A shot with its own `wan_motion_prompt` gets its own name, so changing
    the video prompt makes a new clip instead of reusing one made from a different prompt."""
    w = shot.get("wan_motion_prompt")
    return f"{shot['id']}_{keyframe_hash}" if not w else f"{shot['id']}_{input_hash(keyframe_hash, w)}"
