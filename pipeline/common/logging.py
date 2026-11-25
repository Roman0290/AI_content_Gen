"""Append one JSON line per model call to runs.jsonl."""
import json
import time
from contextlib import contextmanager
from datetime import datetime, timezone

from .config import RUNS_LOG


def log_call(**fields) -> None:
    record = {"ts": datetime.now(timezone.utc).isoformat(), **fields}
    with RUNS_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


@contextmanager
def timed_call(stage: str, model: str, params: dict, seed=None, cost_usd: float = 0.0):
    """Usage: with timed_call("keyframes", "flux-schnell", {...}, seed=42) as rec: rec["output"] = path"""
    rec = {"stage": stage, "model": model, "params": params, "seed": seed, "cost_usd": cost_usd}
    start = time.perf_counter()
    try:
        yield rec
        rec["status"] = "ok"
    except Exception as e:
        rec["status"] = "error"
        rec["error"] = repr(e)
        raise
    finally:
        rec["latency_s"] = round(time.perf_counter() - start, 3)
        log_call(**rec)
