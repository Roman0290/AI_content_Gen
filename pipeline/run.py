"""Run the whole pipeline in order (same as `make film`). Each stage is cached."""
import importlib
import sys

STAGES = ["validate", "reference", "keyframes", "narration", "shots", "music", "assemble"]

if __name__ == "__main__":
    sys.argv = sys.argv[:1]
    for name in STAGES:
        print(f"\n== {name} ==", flush=True)
        mod = importlib.import_module(f"pipeline.{name}")
        (mod.validate if name == "validate" else mod.main)()
