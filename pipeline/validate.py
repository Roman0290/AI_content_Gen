"""Validate storyboard.json against the JSON Schema. Exits non-zero on failure."""
import json
import sys

from jsonschema import Draft202012Validator

from pipeline.common.config import SCHEMA, load_storyboard


def validate() -> dict:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    sb = load_storyboard()
    errors = sorted(Draft202012Validator(schema).iter_errors(sb), key=lambda e: list(e.path))
    if errors:
        for e in errors:
            print(f"storyboard.json:{'/'.join(map(str, e.path)) or '<root>'}: {e.message}", file=sys.stderr)
        sys.exit(1)
    total = sum(s["duration_s"] for s in sb["shots"])
    if not 60 <= total <= 90:
        print(f"warning: total duration {total}s is outside 60-90s", file=sys.stderr)
    print(f"storyboard.json valid: {len(sb['shots'])} shots, {total}s")
    return sb


if __name__ == "__main__":
    validate()
