"""Stage 1: one keyframe per shot, conditioned on the character reference sheets.

Reads  storyboard.json, outputs/reference/manifest.json
Writes outputs/keyframes/<shot>_<hash>.png and outputs/keyframes/manifest.json

Cache key: model, full prompt, seed, size and the bytes of each reference sheet, so a new
reference sheet or an edited image_prompt regenerates only the affected shots.

    python -m pipeline.keyframes                 # all shots
    python -m pipeline.keyframes --shot shot_05  # one shot
"""
import argparse
import hashlib
import json
import sys

from pipeline.common.cache import cached_path, input_hash, is_cached
from pipeline.common.cloudflare import IMAGE_MODEL, generate_image
from pipeline.common.config import OUTPUTS, ROOT, load_storyboard
from pipeline.common.logging import timed_call
from pipeline.common.retry import with_retry

OUT = OUTPUTS / "keyframes"
MANIFEST = OUT / "manifest.json"
REF_MANIFEST = OUTPUTS / "reference" / "manifest.json"
ORDINAL = ["first", "second", "third", "fourth"]


def build_prompt(sb: dict, shot: dict, chars: list[dict]) -> str:
    who = " ".join(
        f"The {c['id'].replace('_', ' ')} is the person in the {ORDINAL[i]} reference image ({c['description']}); "
        "keep her face, hair and clothes exactly the same."
        for i, c in enumerate(chars)
    )
    return (
        f"{shot['image_prompt']}. {who} "
        f"Art style: {sb['style']['description']}. Vertical 9:16 frame, characters fully inside the frame, "
        "no text, no captions, no watermark."
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shot")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    sb = load_storyboard()
    if not REF_MANIFEST.exists():
        sys.exit("No reference sheets yet: run `python -m pipeline.reference` first.")
    refs = json.loads(REF_MANIFEST.read_text())
    w, h = sb.get("format", {}).get("width", 720), sb.get("format", {}).get("height", 1280)
    chars_by_id = {c["id"]: c for c in sb["characters"]}
    old = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    manifest, failed = {}, []

    for shot in sb["shots"]:
        sid = shot["id"]
        if shot.get("keyframe_from"):  # cutaway: uses another shot's keyframe, nothing to generate
            continue
        chars = [chars_by_id[c] for c in shot.get("characters", [])][:4]
        ref_paths = [ROOT / refs[c["id"]]["file"] for c in chars]
        prompt = build_prompt(sb, shot, chars)
        ref_digest = [hashlib.sha256(p.read_bytes()).hexdigest()[:16] for p in ref_paths]
        key = input_hash("keyframe-v1", IMAGE_MODEL, prompt, shot.get("seed"), w, h, ref_digest)
        out = cached_path(OUT, sid, key, "png")

        if args.shot in (None, sid) and (args.force or not is_cached(out)):
            try:
                with timed_call("keyframes", IMAGE_MODEL, {"shot": sid, "prompt": prompt, "w": w, "h": h,
                                                           "refs": [str(p.relative_to(ROOT)) for p in ref_paths]},
                                seed=shot.get("seed")) as rec:
                    out.write_bytes(with_retry(generate_image)(prompt, w, h, shot.get("seed"), ref_paths))
                    rec["output"] = str(out.relative_to(ROOT))
                status = "new"
            except Exception as e:
                print(f"{sid} FAILED {type(e).__name__}: {str(e)[:160]}")
                failed.append(sid)
                if sid in old:
                    manifest[sid] = {**old[sid], "stale": True}
                continue
        elif is_cached(out):
            status = "cached"
        else:
            if sid in old:
                manifest[sid] = {**old[sid], "stale": True}
            continue
        manifest[sid] = {"file": str(out.relative_to(ROOT)), "hash": key, "model": IMAGE_MODEL,
                         "characters": [c["id"] for c in chars]}
        print(f"{sid} [{status}] {out.relative_to(ROOT)}")

    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"\n{len(manifest)} keyframes in manifest, {len(failed)} failed.")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
