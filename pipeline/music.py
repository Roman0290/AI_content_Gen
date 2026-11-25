"""Stage 3: music. Generates score candidates with ACE-Step on a Kaggle GPU, then selects one.

    python -m pipeline.music             # generate candidates (skipped if they exist for these prompts)
    python -m pipeline.music --choose B  # copy candidate B to outputs/music/chosen.wav (also storyboard music.chosen)

Candidates are cached by a hash of their prompts, seeds and duration.
Writes outputs/music/candidates/<name>.wav, outputs/music/candidates/timings.json, outputs/music/chosen.wav
"""
import argparse
import json
import shutil
import sys

from pipeline.common import kaggle_job
from pipeline.common.cache import input_hash
from pipeline.common.config import OUTPUTS, ROOT, load_storyboard
from pipeline.common.logging import log_call
from pipeline.common.timeline import build

JOB_DIR = ROOT / "notebooks" / "acestep_music"
OUT = OUTPUTS / "music"
CAND = OUT / "candidates"


def candidates(sb: dict, duration: int) -> list[dict]:
    base = sb["music"]["prompt"]
    variants = sb["music"].get("candidates") or [
        {"name": "A", "prompt": base, "seed": 11},
    ]
    return [{"name": v["name"], "prompt": v["prompt"], "lyrics": "[instrumental]", "duration": duration,
             "seed": v["seed"], "steps": 60} for v in variants]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--choose")
    args = ap.parse_args()
    sb = load_storyboard()

    if args.choose:
        src = CAND / f"{args.choose}.wav"
        if not src.exists():
            sys.exit(f"no candidate {src}")
        shutil.copy(src, OUT / "chosen.wav")
        print(f"chosen: {args.choose} -> outputs/music/chosen.wav")
        return

    duration = int(build(sb)["total"]) + 2
    jobs = candidates(sb, duration)
    h = input_hash("music-v1", jobs)
    stamp = CAND / "hash.txt"
    if stamp.exists() and stamp.read_text().strip() == h and all((CAND / f"{j['name']}.wav").exists() for j in jobs):
        print("music candidates cached:", ", ".join(j["name"] for j in jobs))
    else:
        code = (JOB_DIR / "acestep_music.py").read_text().replace("__JOBS__", json.dumps(jobs))
        build_dir = JOB_DIR / "build"
        build_dir.mkdir(exist_ok=True)
        (build_dir / "acestep_music.py").write_text(code)
        kid = kaggle_job.write_metadata(build_dir, "heritage-short-music", "Heritage Short music", "acestep_music.py")
        kaggle_job.run(build_dir, kid, CAND, "music", {"model": "ACE-Step-v1-3.5B", "jobs": jobs})
        timings = json.loads((CAND / "timings.json").read_text())
        if all((CAND / f"{j['name']}.wav").exists() for j in jobs):
            stamp.write_text(h)  # only mark as cached when every candidate exists
        for j in timings["jobs"]:  # one runs.jsonl line per generated candidate
            log_call(stage="music", model="ACE-Step-v1-3.5B", params={k: j[k] for k in ("name", "prompt", "duration")},
                     seed=j["seed"], status="ok" if j["status"] == "ok" else "error", latency_s=j["seconds"],
                     gpu=timings["gpu"], cost_usd=0.0, output=f"outputs/music/candidates/{j['name']}.wav")
            print(f"{j['name']}: {j['status']} in {j['seconds']}s")
    if not any((CAND / f"{j['name']}.wav").exists() for j in jobs):
        sys.exit("no music candidates were produced; see outputs/music/candidates/timings.json")
    chosen = sb["music"].get("chosen")
    if chosen and (CAND / f"{chosen}.wav").exists():
        shutil.copy(CAND / f"{chosen}.wav", OUT / "chosen.wav")
        print(f"chosen (storyboard): {chosen}")
    else:
        print("listen to outputs/music/candidates/*.wav and run: python -m pipeline.music --choose <name>")


if __name__ == "__main__":
    main()
