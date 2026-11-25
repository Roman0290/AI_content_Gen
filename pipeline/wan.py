"""Moving shots with Wan 2.2 TI2V-5B on a Kaggle GPU (part of stage 2; slow, so run separately).

    python -m pipeline.wan                    # animate every shot that has no Wan clip for its current keyframe
    python -m pipeline.wan --budget 90        # stop starting new clips after 90 GPU minutes

Uploads the needed keyframes + jobs.json as a private Kaggle dataset, runs notebooks/wan22_i2v/wan_i2v.py,
downloads clips to outputs/shots/wan/<shot>_<keyframe hash>.mp4. Then `python -m pipeline.shots` uses them;
shots without a Wan clip keep the pan-and-zoom fallback. A changed keyframe gets a new hash, so only that
shot is re-animated. Cutaway shots (keyframe_from) are not animated: their close push-in is the point.
"""
import argparse
import json
import os
import shutil
import subprocess

from pipeline.common import kaggle_job
from pipeline.common.config import OUTPUTS, ROOT, load_storyboard
from pipeline.common.logging import log_call

JOB_DIR = ROOT / "notebooks" / "wan22_i2v"
WAN_DIR = OUTPUTS / "shots" / "wan"
PRIORITY = ["shot_05", "shot_06", "shot_01", "shot_09", "shot_03", "shot_02", "shot_04", "shot_10", "shot_12"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, default=150, help="GPU minutes before no new clip is started")
    ap.add_argument("--steps", type=int, default=25)
    ap.add_argument("--resume", help="kernel id already running on Kaggle: just wait and download")
    ap.add_argument("--account", default="2" if os.getenv("KAGGLE_USERNAME2") else "",
                    help='Kaggle account suffix: "" or "2" (default: 2 if KAGGLE_USERNAME2 is set)')
    args = ap.parse_args()
    kaggle_job.use_account(args.account)
    sb = load_storyboard()
    kf = json.loads((OUTPUTS / "keyframes" / "manifest.json").read_text())
    style = sb["style"]["description"]

    shots = sorted((s for s in sb["shots"] if not s.get("keyframe_from") and s["id"] in kf),
                   key=lambda s: PRIORITY.index(s["id"]) if s["id"] in PRIORITY else 99)
    todo = [s for s in shots if not (WAN_DIR / f"{s['id']}_{kf[s['id']]['hash']}.mp4").exists()]
    if not todo:
        print("all Wan clips cached")
        return

    data = JOB_DIR / "build" / "data"
    if data.exists():
        shutil.rmtree(data)
    data.mkdir(parents=True)
    jobs = []
    for s in todo:
        src = ROOT / kf[s["id"]]["file"]
        shutil.copy(src, data / src.name)
        jobs.append({"shot": s["id"], "keyframe": src.name, "out_name": f"{s['id']}_{kf[s['id']]['hash']}",
                     "seed": s.get("seed", 0), "prompt": f"{s['motion_prompt']}. {s['image_prompt']}. "
                     f"Hand-painted 2D animation, gentle natural motion. {style}"})
    cfg = {"width": 480, "height": 832, "frames": 49, "steps": args.steps, "budget_min": args.budget, "jobs": jobs}
    (data / "jobs.json").write_text(json.dumps(cfg, indent=2))

    if args.resume:
        return collect(cfg, args.resume, push=False)

    user = kaggle_job.username()
    ds = f"{user}/heritage-short-keyframes"
    (data / "dataset-metadata.json").write_text(json.dumps(
        {"title": "heritage-short-keyframes", "id": ds, "licenses": [{"name": "CC0-1.0"}]}))
    k = kaggle_job._kaggle
    exists = "heritage-short-keyframes" in k("datasets", "list", "--mine", "-s", "heritage-short-keyframes", check=False)
    print(k("datasets", "version", "-p", str(data), "-m", "keyframes") if exists
          else k("datasets", "create", "-p", str(data)))
    k("datasets", "status", ds, check=False)

    run_dir = JOB_DIR / "build" / "kernel"
    run_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(JOB_DIR / "wan_i2v.py", run_dir / "wan_i2v.py")
    kid = kaggle_job.write_metadata(run_dir, "heritage-short-wan", "heritage-short-wan", "wan_i2v.py", [ds])
    collect(cfg, kid, run_dir=run_dir)


def collect(cfg: dict, kid: str, run_dir=None, push: bool = True) -> None:
    out = OUTPUTS / "shots" / "wan_download"
    kaggle_job.run(run_dir or JOB_DIR / "build", kid, out, "shots_wan", {"model": "Wan2.2-TI2V-5B", **{k_: v for k_, v in cfg.items() if k_ != "jobs"},
                                                   "shots": [j["shot"] for j in cfg["jobs"]]}, timeout_s=5 * 3600, push=push)
    WAN_DIR.mkdir(parents=True, exist_ok=True)
    t = json.loads((out / "timings.json").read_text())
    for j in t["jobs"]:
        clip = out / f"{j['out_name']}.mp4"
        ok = j["status"] == "ok" and clip.exists()
        if ok:
            shutil.move(str(clip), WAN_DIR / clip.name)
        log_call(stage="shots_wan", model="Wan2.2-TI2V-5B", params={"shot": j["shot"], "w": cfg["width"],
                 "h": cfg["height"], "frames": cfg["frames"], "steps": cfg["steps"], "strategy": j.get("strategy"),
                 "text_encoder": t.get("text", {}).get("mode")},
                 seed=j["seed"], status="ok" if ok else j["status"][:80], latency_s=j.get("seconds"), gpu=t["gpu"],
                 peak_gb=j.get("peak_gb"), cost_usd=0.0)
        print(f"{j['shot']}: {j['status']} {j.get('seconds', '')}s {j.get('strategy', '')} {j.get('peak_gb', '')}GB")
    print(f"setup {t.get('setup_s')}s, total {t.get('total_min')} min; see {out / 'progress.log'}")


if __name__ == "__main__":
    main()
