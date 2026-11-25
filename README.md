# If I Come and Find It (እኔ መጥቼ ካገኘሁት)

A 75-second AI-made short film about a scene every Habesha child knows: Mom asks for her bag, you can't
find it, she comes in angry and finds it in one second; and, busy at the stove, she answers "put it on my
head!". Narrated in **Amharic** with **English subtitles**, made by a code pipeline from one file,
`storyboard.json`.

Outputs: `outputs/final/film_9x16.mp4` (vertical, main) and `outputs/final/film_16x9.mp4`.

## Run it

```bash
git clone <this repo> && cd AI_content_Gen
make setup                 # python3 -m venv .venv + pip install -r requirements.txt
cp .env.example .env       # add your keys (see below)
make smoke                 # one call per provider, logged to runs.jsonl
make film                  # the whole film from storyboard.json
```

`make film` runs: validate → reference → keyframes → narration → shots → music → assemble.
Every stage is cached by a hash of its inputs, so a second `make film` makes **no model calls**, and editing
one line of `storyboard.json` regenerates only what depends on it.

Optional, slow (GPU on Kaggle): `make wan` animates keyframes with Wan 2.2; without it, shots use a
pan-and-zoom over the keyframe. `make radio-cut` builds the narration-only prototype used for user test 1.

### Regenerate one shot
```bash
# edit shots[shot_05].narration (or image_prompt) in storyboard.json, then:
make film      # only shot_05's TTS clip (or keyframe) is regenerated; check the new line in runs.jsonl
```

## Keys (all free, no card)

| Variable | Where | Used for |
|---|---|---|
| `GEMINI_API_KEY` (+ optional `GEMINI_API_KEY2`) | Google AI Studio | Amharic narration (Gemini 3.8 Flash TTS) |
| `CF_ACCOUNT_ID`, `CF_API_TOKEN` | Cloudflare → Workers AI | keyframes (FLUX.2 klein 9B) |
| `KAGGLE_USERNAME`, `KAGGLE_KEY` | kaggle.com → Settings → API (phone-verified) | music (ACE-Step) and video (Wan 2.2) on GPU |

Needs Python 3.12 and FFmpeg 6 with libass. Fonts: Noto Sans Ethiopic.

## What it costs

$0. The limits are free-tier quotas, not money: 10 TTS requests per model per day, ~15 FLUX.2 klein images
per day on Cloudflare, ~30 Kaggle GPU hours per week. Measured latencies, GPU minutes and list-price
equivalents are in [COSTS.md](COSTS.md).

## Repository

| Path | What |
|---|---|
| `storyboard.json` | the contract: 11 shots with reasons, prompts, Amharic lines, subtitles, voices, music |
| `schema/` | JSON Schema, checked before every run |
| `pipeline/` | one module per stage; `pipeline/common/` holds cache, retry, logging, timeline, provider clients |
| `notebooks/` | the Kaggle GPU jobs (ACE-Step music, Wan 2.2 image-to-video) |
| `scripts/` | smoke test, experiments, one-off repair |
| `runs.jsonl` | one line per model call |
| `outputs/` | every generated file, kept for inspection |

Docs: [DESIGN](DESIGN.md) · [ARCHITECTURE](ARCHITECTURE.md) · [EXPERIMENTS](EXPERIMENTS.md) ·
[FAILURES](FAILURES.md) · [COSTS](COSTS.md) · [ETHICS](ETHICS.md) · [report](docs/report.md)

The film is labelled "Made with AI" on its end card and is posted with the platform's AI label on.
