"""Stage 2: one moving clip per shot, at the shot's fitted length (from the narration manifest).

Two methods, chosen per shot:
  wan     a Wan 2.2 image-to-video clip made on Kaggle exists in outputs/shots/wan/<shot>_<keyframe hash>.mp4
          (see notebooks/wan22_i2v_kaggle.ipynb); it is retimed to the shot length.
  pan     fallback with no GPU: a slow push-in, pull-out or pan over the keyframe (Ken Burns), so the film
          is always complete even when the GPU queue or quota fails.

Reads  outputs/keyframes/manifest.json, outputs/narration/manifest.json, storyboard.json
Writes outputs/shots/<shot>_<hash>.mp4 and outputs/shots/manifest.json (720x1280, 25 fps, no audio)
"""
import argparse
import json
import subprocess
import sys

from pipeline.common.cache import cached_path, input_hash, is_cached
from pipeline.common.config import OUTPUTS, ROOT, load_storyboard
from pipeline.common.timeline import build

OUT = OUTPUTS / "shots"
WAN_DIR = OUT / "wan"
MANIFEST = OUT / "manifest.json"
W, H, FPS = 720, 1280, 25


def pan_filter(motion: str, frames: int) -> str:
    """Pick a camera move from the motion prompt. Upscaled first so the zoom does not jitter."""
    m = motion.lower()
    z = f"min(1+0.12*on/{frames},1.12)"                      # push in by 12 %
    if "pull-out" in m or "pull out" in m:
        z = f"max(1.12-0.12*on/{frames},1)"
    x, y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    if "close" in m and "face" in m:  # tight push-in towards the upper third, where faces are
        z, y = f"min(1.45+0.25*on/{frames},1.7)", "ih/4-(ih/zoom/4)"
    if "pan" in m and "push" not in m:
        z, x = "1.1", f"(iw-iw/zoom)*on/{frames}"              # slow pan left to right
    return (f"scale={W * 2}:{H * 2},zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={W}x{H}:fps={FPS},"
            "format=yuv420p")


def render_pan(keyframe: str, motion: str, dur: float, out) -> None:
    frames = round(dur * FPS)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", keyframe, "-vf", pan_filter(motion, frames),
                    "-frames:v", str(frames), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-an", str(out)],
                   check=True)


def render_wan(clip: str, dur: float, out) -> None:
    """Fit a ~5 s Wan clip to the shot: slow it down up to 1.5x, then hold the last frame."""
    src = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", clip],
                               capture_output=True, text=True, check=True).stdout)
    stretch = min(dur / src, 1.5)
    vf = (f"setpts={stretch:.4f}*PTS,fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
          f"tpad=stop_mode=clone:stop_duration={dur},format=yuv420p")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", clip, "-vf", vf, "-t", str(dur), "-c:v", "libx264",
                    "-preset", "veryfast", "-crf", "18", "-an", str(out)], check=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shot")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    sb = load_storyboard()
    tl = {s["id"]: s for s in build(sb)["shots"]}
    kf_path = OUTPUTS / "keyframes" / "manifest.json"
    if not kf_path.exists():
        sys.exit("No keyframes: run `python -m pipeline.keyframes` first.")
    kf = json.loads(kf_path.read_text())
    manifest = {}
    for shot in sb["shots"]:
        sid, dur = shot["id"], tl[shot["id"]]["dur"]
        kid = shot.get("keyframe_from", sid)  # cutaway: reuse another shot's keyframe
        if kid not in kf:
            print(f"{sid}: no keyframe, skipped")
            continue
        wan = WAN_DIR / f"{sid}_{kf[kid]['hash']}.mp4"
        method = "wan" if wan.exists() else "pan"
        source = str(wan) if method == "wan" else str(ROOT / kf[kid]["file"])
        h = input_hash("shot-v1", method, kf[kid]["hash"], dur, shot["motion_prompt"] if method == "pan" else "")
        out = cached_path(OUT, sid, h, "mp4")
        status = "cached"
        if args.shot in (None, sid) and (args.force or not is_cached(out)):
            (render_wan if method == "wan" else render_pan)(source, *(() if method == "wan" else (shot["motion_prompt"],)), dur, out)
            status = "new"
        manifest[sid] = {"file": str(out.relative_to(ROOT)), "hash": h, "method": method, "dur": dur,
                         "keyframe": kf[kid]["file"], "keyframe_from": kid if kid != sid else None,
                         "keyframe_stale": kf[kid].get("stale", False)}
        print(f"{sid} [{status:>6}] {method:<4} {dur:5.2f}s {out.relative_to(ROOT)}")
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
