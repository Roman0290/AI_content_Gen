"""Kaggle GPU job: score candidates for the Heritage Short with ACE-Step (v1, 3.5B, Apache 2.0).
Reads jobs.json (written by pipeline/music.py and inlined below), writes /kaggle/working/<name>.wav and timings.json.
"""
import json
import os
import subprocess
import sys
import time

JOBS = json.loads(r'''__JOBS__''')

os.chdir("/kaggle/working")
t0 = time.time()
if not os.path.exists("ACE-Step"):
    subprocess.run(["git", "clone", "--depth", "1", "https://github.com/ace-step/ACE-Step.git"], check=True)
# ACE-Step pins versions (spacy==3.8.4, transformers==4.50.0, ...) that have no wheels for Kaggle's Python 3.13
# (F14). Install the package without its pins, then compatible versions one by one; a failing optional
# package (Japanese/Korean lyric helpers) must not stop an instrumental run. Kaggle's torch is kept.
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--no-deps", "-e", "ACE-Step"], check=True)
DEPS = ["diffusers>=0.33,<0.36", "transformers>=4.50,<4.57", "accelerate>=1.6", "datasets>=3.4,<4",
        "librosa>=0.11", "loguru", "pypinyin", "pytorch_lightning>=2.5", "soundfile", "py3langid",
        "hangul-romanize", "num2words", "spacy>=3.8.5,<3.9", "peft", "click", "cutlet", "fugashi[unidic-lite]"]
install_log = {}
for dep in DEPS:
    r = subprocess.run([sys.executable, "-m", "pip", "install", "-q", dep], capture_output=True, text=True)
    install_log[dep] = "ok" if r.returncode == 0 else r.stderr.strip().splitlines()[-1][:200]
    print("pip", dep, install_log[dep], flush=True)
sys.path.insert(0, "/kaggle/working/ACE-Step")
setup_s = time.time() - t0

import torch  # noqa: E402
from acestep.pipeline_ace_step import ACEStepPipeline  # noqa: E402

print("GPU:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "none", flush=True)
pipe = ACEStepPipeline(checkpoint_dir=None, dtype="float16", torch_compile=False, cpu_offload=True)
timings = {"setup_s": round(setup_s, 1), "gpu": torch.cuda.get_device_name(0), "python": sys.version.split()[0],
           "install": install_log, "jobs": []}
for job in JOBS:
    s = time.time()
    path = f"/kaggle/working/{job['name']}.wav"
    try:
        pipe(prompt=job["prompt"], lyrics=job.get("lyrics", "[instrumental]"), audio_duration=job["duration"],
             infer_step=job.get("steps", 60), guidance_scale=15.0, scheduler_type="euler", cfg_type="apg",
             omega_scale=10.0, manual_seeds=[job["seed"]], save_path=path, format="wav")
        status = "ok"
    except Exception as e:  # keep going: one failed candidate should not lose the others
        status = f"error: {e!r}"
    timings["jobs"].append({**job, "status": status, "seconds": round(time.time() - s, 1)})
    print(job["name"], status, round(time.time() - s, 1), "s", flush=True)
    json.dump(timings, open("/kaggle/working/timings.json", "w"), indent=2)
subprocess.run(["rm", "-rf", "/kaggle/working/ACE-Step"])  # only the audio comes back
