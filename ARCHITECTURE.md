# Architecture

## One contract, many stages

`storyboard.json` is the only file a person edits. It is validated against `schema/storyboard.schema.json`
before every run. Every stage reads it, writes its outputs plus a `manifest.json` into `outputs/<stage>/`,
and later stages read those manifests. Stages never call each other.

```
storyboard.json ──validate──┐
                            ▼
  reference   FLUX.2 klein 9B (Cloudflare)   → outputs/reference/   character sheets
  keyframes   FLUX.2 klein 9B + sheets       → outputs/keyframes/   one image per shot
  narration   Gemini 3.8 Flash TTS           → outputs/narration/   one Amharic clip per shot, fitted shot lengths
  shots       Wan 2.2 TI2V-5B (Kaggle) or    → outputs/shots/       one clip per shot at its fitted length
              FFmpeg pan-and-zoom fallback
  music       ACE-Step (Kaggle GPU)          → outputs/music/       candidates + chosen.wav
  subtitles   from storyboard + timings      → outputs/subtitles/   .srt and .ass (both formats)
  assemble    FFmpeg                         → outputs/final/       film_9x16.mp4, film_16x9.mp4
                                               outputs/radio_cut/   narration-only prototype
```

| Stage | Reads | Writes | Command |
|---|---|---|---|
| validate | storyboard, schema | — | `make validate` |
| reference | style, characters | `reference/manifest.json` | `make reference` |
| keyframes | shots, reference manifest | `keyframes/manifest.json` | `make keyframes` |
| narration | shots[].narration, speaker, tts_tag, voices | `narration/manifest.json` (audio_s, fitted_s) | `make narration` |
| shots | keyframe + narration manifests, motion_prompt | `shots/manifest.json` (method wan/pan) | `make shots` |
| wan (optional, slow) | keyframes, motion/image prompts | `shots/wan/*.mp4` | `make wan` |
| music | music.candidates, film length | `music/candidates/*.wav`, `chosen.wav` | `make music` |
| assemble | all manifests, `pipeline/common/timeline.py` | `final/*.mp4` | `make assemble` |

**Timeline.** `pipeline/common/timeline.py` turns the storyboard plus narration manifest into start times. A
shot lasts `max(planned duration, narration length + 0.6 s)`, each line starts 0.3 s after the cut. Subtitles
and assembly both use this one function, so audio, picture and subtitles cannot drift apart.

## Caching

Every output file is named `<shot>_<hash>.<ext>`, where the hash covers everything that affects it:

| Stage | Hash inputs |
|---|---|
| reference | model, prompt, seed, size, bytes of the `based_on` sheet |
| keyframes | model, full prompt, seed, size, sha256 of each reference sheet used |
| narration | TTS model, voice, spoken text (including `[tts_tag]`) |
| shots | method, keyframe hash, fitted duration, motion prompt |
| Wan clips | keyframe hash (`shots/wan/<shot>_<keyframe hash>.mp4`) |
| music | all candidate prompts, seeds, duration |

If the file exists, the stage skips the model call. So editing one narration line in `storyboard.json`
regenerates exactly one TTS clip (one new line in `runs.jsonl`), then that shot's length, subtitles and the
final mix; every other stage reports `cached`. A changed reference sheet changes the hash of every keyframe
that uses it, and nothing else.

## Failure handling

| Failure | Handling | Where |
|---|---|---|
| Transient (408/429 per-minute/5xx/timeouts) | exponential backoff, 6 attempts | `common/retry.py` |
| Daily quota (Gemini `PerDay`, Cloudflare 4006) | not retried (would wait ~20 h); fail fast | `retry.is_daily_quota` |
| Gemini key out of daily quota | switch to the next key (`GEMINI_API_KEY2`, ...), same model | `common/gemini.py` |
| Main TTS model unavailable | lite model only with `--allow-fallback` (it sounded unnatural, E03); clips from another model are stale and regenerated later | `narration.py` |
| Main text model overloaded (503) | fall back to gemini-3.5-flash | `smoke_test.py` |
| A shot fails | the previous clip stays in the manifest marked `stale`, so assembly still produces a film | narration, keyframes |
| No GPU / Wan fails | pan-and-zoom over the keyframe, so the film is always complete | `shots.py` |
| Wan fp16 overflow | middle frame checked for black output; marked `suspect` and not used | `wan_i2v.py` |
| Kaggle job runs long | time budget: no new clip is started after `--budget` minutes | `wan.py` |
| TTS returns a WAV with metadata | parsed as WAV, raw response kept as `.source.wav` | `gemini.split_wav` (F09) |

## Logging

`runs.jsonl` gets one line per model call (or Kaggle job): timestamp, stage, model, parameters (prompt,
voice, size, shot), seed, status, error, latency, output path, cost, and for TTS the key index (never the key).
Kaggle jobs also log GPU minutes and the GPU type; per-clip timings come from the job's `timings.json`.

## Secrets

Keys live only in `.env` (git-ignored). `.env.example` lists the variables. Logs record which key number was
used, not the key.
