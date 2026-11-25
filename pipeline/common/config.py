"""Paths and environment loading."""
import json
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

STORYBOARD = ROOT / "storyboard.json"
SCHEMA = ROOT / "schema" / "storyboard.schema.json"
OUTPUTS = ROOT / "outputs"
RUNS_LOG = ROOT / "runs.jsonl"


def env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing {name}; copy .env.example to .env and fill it in.")
    return value


def load_storyboard() -> dict:
    return json.loads(STORYBOARD.read_text(encoding="utf-8"))
