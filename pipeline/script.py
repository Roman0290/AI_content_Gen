"""Stage 0: story notes -> storyboard draft / translation (Gemini Flash)."""
from pipeline.common.cache import cached_path, input_hash, is_cached
from pipeline.common.config import OUTPUTS, load_storyboard
from pipeline.common.logging import timed_call
from pipeline.common.retry import with_retry


def main() -> None:
    sb = load_storyboard()
    raise NotImplementedError("TODO: implement script stage")


if __name__ == "__main__":
    main()
