"""Character reference sheets, generated before any keyframe and passed to every keyframe call.

Reads  storyboard.json (style, characters, format)
Writes outputs/reference/<character>_<hash>.png and outputs/reference/manifest.json

A character with `based_on` (e.g. the grown-up daughter) is generated with that character's sheet
as an input image, so the adult still resembles the child.
"""
import argparse
import json

from pipeline.common.cache import cached_path, input_hash, is_cached
from pipeline.common.cloudflare import IMAGE_MODEL, generate_image
from pipeline.common.config import OUTPUTS, ROOT, load_storyboard
from pipeline.common.logging import timed_call
from pipeline.common.retry import with_retry

OUT = OUTPUTS / "reference"
MANIFEST = OUT / "manifest.json"
W, H = 1280, 720  # landscape sheet: several poses side by side


def sheet_prompt(style: str, ch: dict) -> str:
    return (
        f"Character reference sheet of one person: {ch['description']}. "
        "Show the same person three times side by side: full body front view, full body three-quarter view, "
        "and a close-up of the face. Plain warm off-white background, even lighting, no text, no labels. "
        f"Art style: {style}."
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    sb = load_storyboard()
    style = sb["style"]["description"]
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}

    # characters without based_on first, so their sheets exist when a dependent one needs them
    for ch in sorted(sb["characters"], key=lambda c: bool(c.get("based_on"))):
        refs = [ROOT / manifest[ch["based_on"]]["file"]] if ch.get("based_on") else []
        prompt = sheet_prompt(style, ch)
        if refs:
            prompt = f"The same person as in the reference image, now grown up. {prompt}"
        seed = ch.get("seed", 1000)
        h = input_hash("reference-v1", IMAGE_MODEL, prompt, seed, W, H, [r.read_bytes().hex()[:64] for r in refs])
        out = cached_path(OUT, ch["id"], h, "png")
        if args.force or not is_cached(out):
            with timed_call("reference", IMAGE_MODEL, {"character": ch["id"], "prompt": prompt, "w": W, "h": H,
                                                       "refs": [str(r.relative_to(ROOT)) for r in refs]}, seed=seed) as rec:
                out.write_bytes(with_retry(generate_image)(prompt, W, H, seed, refs))
                rec["output"] = str(out.relative_to(ROOT))
            status = "new"
        else:
            status = "cached"
        manifest[ch["id"]] = {"file": str(out.relative_to(ROOT)), "hash": h, "model": IMAGE_MODEL}
        MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
        print(f"{ch['id']:<16} [{status}] {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
