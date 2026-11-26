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
from pathlib import Path
import sys

from pipeline.common.cache import cached_path, input_hash, is_cached, wan_name
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


def render_wan(clip: str, dur: float, out, use_s: float | None = None) -> None:
    """Fit a ~2 s Wan clip to the shot without freezing: play it slowed down (up to 1.25x), then keep moving
    with a slow camera push-in over its last frame (user test 2: the frozen second half looked dead)."""
    src = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", clip],
                               capture_output=True, text=True, check=True).stdout)
    if use_s:  # only the first use_s seconds, before the faces drift (user test 2)
        src = min(src, use_s)
    stretch = min(dur / src, 1.25)
    part = min(src * stretch, dur)
    tmp = Path(str(out) + ".part.mp4")
    last = Path(str(out) + ".last.png")
    vf = f"setpts={stretch:.4f}*PTS,fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},format=yuv420p"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", clip, "-vf", vf, "-t", f"{part:.3f}", "-c:v", "libx264",
                    "-preset", "veryfast", "-crf", "18", "-an", str(tmp)], check=True)
    rest = round((dur - part) * FPS)
    if rest < 2:
        tmp.replace(out)
        return
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-sseof", "-0.1", "-i", str(tmp), "-frames:v", "1", "-update", "1",
                    str(last)], check=True)
    hold = Path(str(out) + ".hold.mp4")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", str(last), "-vf",
                    pan_filter("slow push-in", rest), "-frames:v", str(rest), "-c:v", "libx264", "-preset",
                    "veryfast", "-crf", "18", "-an", str(hold)], check=True)
    lst = Path(str(out) + ".txt")
    lst.write_text(f"file '{tmp.resolve()}'\nfile '{hold.resolve()}'\n")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
                    str(out)], check=True)
    for f in (tmp, last, hold, lst):
        f.unlink(missing_ok=True)


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
        wan = WAN_DIR / f"{wan_name(shot, kf[kid]['hash'])}.mp4"
        method = "wan" if wan.exists() and shot.get("animate", True) else "pan"  # animate:false -> keyframe (drift)
        source = str(wan) if method == "wan" else str(ROOT / kf[kid]["file"])
        h = input_hash("shot-v1", method, kf[kid]["hash"], dur, shot["motion_prompt"] if method == "pan" else "") \
            if method == "pan" else input_hash("shot-v2", method, wan.name, dur, shot.get("wan_use_s"))
        out = cached_path(OUT, sid, h, "mp4")
        status = "cached"
        if args.shot in (None, sid) and (args.force or not is_cached(out)):
            if method == "wan":
                render_wan(source, dur, out, shot.get("wan_use_s"))
            else:
                render_pan(source, shot["motion_prompt"], dur, out)
            status = "new"
        manifest[sid] = {"file": str(out.relative_to(ROOT)), "hash": h, "method": method, "dur": dur,
                         "keyframe": kf[kid]["file"], "keyframe_from": kid if kid != sid else None,
                         "keyframe_stale": kf[kid].get("stale", False)}
        print(f"{sid} [{status:>6}] {method:<4} {dur:5.2f}s {out.relative_to(ROOT)}")
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
