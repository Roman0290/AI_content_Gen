"""Run a script on a Kaggle GPU and download its outputs, using the Kaggle CLI.

The script and its kernel-metadata.json live in notebooks/<job>/; this pushes them as a private kernel,
polls until it finishes, and downloads /kaggle/working into a local folder. Every run is logged.
"""
import json
import re
import os
import shutil
import subprocess
import time
from pathlib import Path

from .config import ROOT, env
from .logging import log_call

KAGGLE = str(ROOT / ".venv" / "bin" / "kaggle")
ACCOUNT = ""  # "" = KAGGLE_USERNAME/KAGGLE_KEY; "2" = KAGGLE_USERNAME2/KAGGLE_KEY2 (a second account's GPU quota)


def use_account(suffix: str) -> None:
    global ACCOUNT
    ACCOUNT = suffix


def username() -> str:
    return env(f"KAGGLE_USERNAME{ACCOUNT}")


def _env() -> dict:
    e = dict(os.environ)
    key = env(f"KAGGLE_KEY{ACCOUNT}")
    e["KAGGLE_USERNAME"] = username()
    e.pop("KAGGLE_API_TOKEN", None)
    e["KAGGLE_KEY"] = key
    if key.startswith("KGAT_"):
        e["KAGGLE_API_TOKEN"] = key  # new-style token (F04)
    return e


def _kaggle(*args, check=True) -> str:
    try:  # a status call once hung for 52 min and froze the poller (F16)
        r = subprocess.run([KAGGLE, *args], capture_output=True, text=True, env=_env(),
                           timeout=600 if args[:2] in (("kernels", "push"), ("datasets", "create"),
                                                       ("datasets", "version"), ("kernels", "output")) else 120)
    except subprocess.TimeoutExpired:
        if check:
            raise RuntimeError(f"kaggle {' '.join(args)} timed out")
        return "timeout"
    if check and r.returncode != 0:
        raise RuntimeError(f"kaggle {' '.join(args)} failed: {r.stdout}{r.stderr}")
    return r.stdout + r.stderr


def write_metadata(job_dir: Path, slug: str, title: str, code_file: str, datasets: list[str] = ()) -> str:
    kid = f"{username()}/{slug}"
    # Kaggle derives the kernel URL from the title; a title that doesn't slugify to `slug` creates a kernel
    # under a different id than the one we poll (F10), so the title is the slug itself.
    meta = {"id": kid, "title": slug, "code_file": code_file, "language": "python", "kernel_type": "script",
            "is_private": True, "enable_gpu": True, "enable_internet": True, "machine_shape": "Gpu",
            "dataset_sources": list(datasets), "kernel_sources": [], "competition_sources": [], "model_sources": []}
    (job_dir / "kernel-metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
    return kid


def run(job_dir: Path, kid: str, out_dir: Path, stage: str, params: dict, poll_s: int = 30,
        timeout_s: int = 3 * 3600, push: bool = True) -> Path:
    """Push (unless resuming), wait, download. Returns out_dir. Logs latency and GPU minutes to runs.jsonl."""
    start = time.time()
    if push:
        print(_kaggle("kernels", "push", "-p", str(job_dir)).strip())
    status = "unknown"
    while time.time() - start < timeout_s:
        time.sleep(poll_s)
        s = _kaggle("kernels", "status", kid, check=False).lower()
        if "404" in s or "not found" in s:
            raise RuntimeError(f"Kaggle kernel {kid} not found while polling: {s.strip()}")
        # Only trust Kaggle's own status field: a network error message (e.g. after the laptop sleeps) contains
        # the word "error" and was once mistaken for a failed job (F18).
        m = re.search(r"kernelworkerstatus\.(\w+)", s)
        if not m:
            print(f"  [{int(time.time() - start):>5}s] status unavailable, retrying: {s.strip()[:120]}", flush=True)
            continue
        status = next((w for w in ("complete", "error", "cancel", "running", "queued") if w in m.group(1)), m.group(1))
        print(f"  [{int(time.time() - start):>5}s] {status}", flush=True)
        if status in ("complete", "error", "cancel"):
            break
    minutes = round((time.time() - start) / 60, 1)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    _kaggle("kernels", "output", kid, "-p", str(out_dir), check=False)
    log_call(stage=stage, model=f"kaggle:{kid}", params=params, status="ok" if status == "complete" else status,
             latency_s=round(time.time() - start, 1), gpu_minutes=minutes, cost_usd=0.0,
             output=str(out_dir.relative_to(ROOT)))
    if status != "complete":
        raise RuntimeError(f"Kaggle job {kid} ended with status {status}; log in {out_dir}")
    return out_dir
