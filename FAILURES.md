# Failures

<!-- Template:
## F01: title
- **What broke:**
- **What I tried:**
- **What fixed it / workaround:**
-->

## F01: Python environment could not be created (2026-11-25)
- **What broke:** `python3 -m venv .venv` failed: `ensurepip is not available`. The system had no pip and no `python3.12-venv`.
- **What I tried:** `sudo apt install python3.12-venv` (not completed); installing `uv` (blocked by the coding agent's permission check).
- **What fixed it:** `python3 -m venv --without-pip .venv`, then the official `get-pip.py` bootstrap into the venv. No sudo needed.

## F02: Gemini TTS rejected `speechConfig` (2026-11-25)
- **What broke:** `400 INVALID_ARGUMENT: Unknown name "speechConfig" at 'generation_config'`. `--list-models` showed no TTS model at all.
- **What I tried:** four model IDs × with/without speech config; all 400 or 404.
- **What fixed it:** google-genai 3.6.1 defaults to the stable `v1` API, which does not expose TTS. Creating the client with `HttpOptions(api_version="v1beta")` made `gemini-3.8-flash-tts` visible and the call succeeded (7.7 s).

## F03: Cloudflare FLUX 400 on `seed` (2026-11-25)
- **What broke:** `AiError: Additional or unevaluated properties '/seed' not allowed` for `@cf/black-forest-labs/flux-1-schnell`.
- **What fixed it:** removed `seed`. Consequence: schnell outputs are not reproducible by seed. Caching by input hash matters even more; test whether FLUX.2 klein accepts a seed.

## F04: Kaggle 401 Unauthorized (2026-11-25)
- **What broke:** basic auth (username + key) returned 401.
- **What fixed it:** the key is a new-style `KGAT_` API token, which uses `Authorization: Bearer <token>`. The smoke test now picks the auth method from the key prefix.

## F05: gemini-3.8-flash 503 "high demand" (2026-11-25)
- **What broke:** three runs, 5 retries each with exponential backoff (51–90 s per run), all 503.
- **What fixed it:** a fallback model (`GEMINI_TEXT_FALLBACK=gemini-3.5-flash`), which answered in 4.7 s. Retries now only fire on transient codes (408/429/5xx); 400/401/404 fail immediately.

## F06: Gemini TTS daily quota: 10 requests per day per model (2026-11-25)
- **What broke:** narration for shot_04 onwards returned `429 RESOURCE_EXHAUSTED`, quotaId `GenerateRequestsPerDayPerProjectPerModel-FreeTier`, quotaValue 10, retryDelay ≈ 74,000 s (20.6 h). The smoke test and E02 voice experiments had already used most of the day's 10 calls.
- **What made it worse:** the retry helper treated every 429 as transient and backed off for ~70 s per shot before failing (6 shots × 70 s wasted).
- **What fixed it:**
  1. `retry.is_daily_quota()`: a 429 with a `PerDay` quota is not retried.
  2. Narration keeps a per-run set of exhausted models and goes straight to the fallback for later shots.
  3. Fallback `gemini-3.8-flash-lite-tts` (its own 10/day quota) voiced shots 04–12 at 3–5 s per call.
  4. The cache keeps finished clips, so a quota-limited run is resumed the next day without repeating calls.
- **Open issue:** shots 01–03 used gemini-3.8-flash-tts and 04–12 the lite model; the same voice name may sound different across the two models. Check by ear; if it does, regenerate 01–03 on the lite model when the quota resets.
- **Lesson:** 12 lines > 10 calls/day. Budget TTS calls: experiments burn the same quota as the film.

## F07: Cloudflare Workers AI daily allocation used up after ~16 images (2026-11-25)
- **What broke:** the second keyframe pass (4 re-prompted shots) returned `429`, code 4006: "you have used up your daily free allocation of 10,000 neurons". Both FLUX.2 klein and FLUX.1 schnell are blocked: the allocation is per account, not per model.
- **What used it:** 1 schnell smoke image, 1 klein test, 3 reference sheets (1280×720) and 11 keyframes (720×1280) on flux-2-klein-9b, so roughly **600–700 neurons per klein-9b image**, about 15 images per day, not the 50–170 the brief estimated for schnell.
- **What made it worse:** the retry helper retried each shot 6 times over ~2 minutes before failing.
- **What fixed it:** code 4006 / "daily free allocation" is now classified as a daily quota and not retried. The 4 previous keyframes stay in the manifest as `stale` placeholders, and the next run regenerates only those 4 after the allocation resets (00:00 UTC = 03:00 EAT).
- **Lesson:** reference sheets + keyframes + one retake pass ≈ 30 images ≈ 2 days of free allocation. Review keyframes in one batch and re-prompt all problems in one pass.

## F08: New Gemini key not picked up (2026-11-25)
- **What broke:** after adding a key from a second Google Cloud project as `GEMINI_API_KEY2`, narration still failed: the code only read `GEMINI_API_KEY` (the exhausted one).
- **What fixed it:** `pipeline/common/gemini.py` reads `GEMINI_API_KEY`, `GEMINI_API_KEY2`, `GEMINI_API_KEY_2`, ... and on a daily-quota 429 switches to the next key and retries the same model. runs.jsonl records the key index (`"key": 1`), never the key. All 8 remaining shots then generated on gemini-3.8-flash-tts; shots 01–03 (key 0) and 04–12 (key 1) use the same model and voices.

## F09: Noise burst at the end of every narration line (2026-11-25)
- **What broke:** listening to the radio cut, a harsh sound at the end of every shot.
- **Diagnosis:** every clip's last 160 ms peaked at full scale (1.000) after ~200 ms of silence, identical in every clip, so not speech. The untrimmed smoke clip showed why: gemini-3.8-flash-tts returns a **complete WAV file** (RIFF header + PCM + a 7,664-byte metadata chunk ending in `digitalsourcetype/trainedAlgorithmicMedia`, i.e. AI-provenance metadata), not bare PCM. My code wrapped it in a second WAV header, so the header played as a click at the start and the metadata as a 160 ms noise burst at the end.
- **What fixed it:** `gemini.split_wav()` parses a RIFF response and keeps only its audio frames; the untouched response is saved next to each clip as `<shot>_<hash>.source.wav` so the provenance metadata is preserved. `scripts/repair_tts_clips.py` extracted the embedded WAV from the 11 existing clips (no new TTS calls) and re-trimmed them (each 0.3–0.6 s shorter). Verified: clip-end peaks 0.01–0.03; no full-scale sample anywhere in the radio cut.
- **Lesson:** listen to outputs, then measure; an API's response format can change between model generations without the SDK telling you.

## F10: Kaggle kernel pushed under a different id than the one polled (2026-11-25)
- **What broke:** the Wan job pushed fine, but Kaggle warned "Your kernel title does not resolve to the specified id" and created `heritage-short-wan-i2v` (from the title "Heritage Short Wan i2v") while the code polled `heritage-short-wan`. The poller would have waited for hours on a kernel that didn't exist.
- **What fixed it:** the kernel title is now the slug itself; polling raises on "not found" instead of looping; `python -m pipeline.wan --resume <kernel id>` re-attaches to a job already running on Kaggle (used for this run, so no GPU time was wasted).

## F11: Couldn't confirm an ACE-Step 1.5 setup in time; used ACE-Step v1 (2026-11-25)
- **What happened:** the brief suggests ACE-Step 1.5. The public Kaggle notebook titled "ACEStep 1.5" actually clones the original `ace-step/ACE-Step` (v1) repo and loads a third-party checkpoint, so it can't be trusted as a 1.5 reference. With the deadline the same day, I used the official ACE-Step v1 pipeline (`ACEStepPipeline`, official 3.5B checkpoint, Apache 2.0), which has a known API and runs on a T4 with CPU offload.
- **Next step:** port `notebooks/acestep_music/` to the ACE-Step 1.5 repo and compare the two on the same prompts (a good EXPERIMENTS entry).

## F12: Gemini image models have no free quota (2026-11-25)
- **What broke:** trying to fix keyframes 07 and 11 by image editing with gemini-3.1-flash-image, gemini-2.5-flash-image and gemini-3.1-flash-lite-image: immediate 429 on both keys (free-tier limit 0), matching the brief (Nano Banana is paid-only). Cloudflare was also out for the day (F07).
- **Workaround:** cutaways. Shot 07 reuses shot 06's keyframe (Mom already furious next to the bag) with a close push-in on her face; shot 11 reuses shot 09's (Mom stressed at the stove). New storyboard field `keyframe_from`. Both now match the story's emotion, which the generated versions did not.

## F13: Wan 2.2 TI2V-5B out of GPU memory on a Kaggle T4 (2026-11-25)
- **What broke:** first Wan run (480×832, 81 frames, 25 steps, fp16, `enable_model_cpu_offload`): `CUDA out of memory` after 16.5 s on the first shot (14.39 GB allocated of 14.56 GB). Every following shot then failed in 0.5 s, because the failed run's memory was never released. 0 of 9 clips; setup alone took 327 s. Total ~7 min of GPU.
- **Notes:** the T4 has no bf16, so the transformer runs in fp16; whole-model offload still needs the full 5B transformer (~10 GB) plus activations on the GPU at once.
- **What I changed:** sequential CPU offload (layers streamed from RAM), VAE tiling, 49 frames instead of 81, `gc.collect()` + `torch.cuda.empty_cache()` after a failure, and stop after 2 consecutive OOMs instead of burning through every shot.
- **Meanwhile:** the film is complete with the pan-and-zoom fallback (`shots.py`), as designed for exactly this case.

## F14: ACE-Step install failed on Kaggle's Python 3.13 (2026-11-25)
- **What broke:** after ~22 min in Kaggle's queue (re-pushed once as version 2), the music job failed in 33 s: `No matching distribution found for spacy==3.8.4`. Kaggle's image now runs Python 3.13; ACE-Step's `requirements.txt` pins spacy 3.8.4 (Python < 3.13), transformers 4.50.0 and others. No music was generated.
- **What fixed it:** `pip install --no-deps -e ACE-Step`, then compatible versions installed one at a time (`spacy>=3.8.5,<3.9`, `transformers>=4.50,<4.57`, `diffusers>=0.33,<0.36`, ...), each result logged in `timings.json["install"]`; a failing optional package (Japanese lyric helpers) no longer stops an instrumental run. Kaggle's own torch is kept.
- **Lesson:** pinned research repos break when the hosted runtime moves on; check the platform's Python version before the first GPU run, and make installs fail soft.

## F15: Second Kaggle account had no internet (2026-11-25)
- **What broke:** the memory-safe Wan job on the second account failed at the first `pip install`: `Failed to resolve 'pypi.org'`. The kernel metadata requests `enable_internet: true`, but Kaggle only grants internet (and GPU) to phone-verified accounts and silently runs without it otherwise. Nothing reached the GPU, so the F13 memory fixes are still untested.
- **Fix:** phone-verify the account (Kaggle → Settings → Phone verification), or run on the verified account after the music job. Next improvement: a 10-second preflight cell that checks internet and `nvidia-smi` and fails loudly before any long setup.

## F16: Music ran but produced nothing; a Kaggle status call hung for 52 minutes (2026-11-25)
- **What broke (music):** version 3 got a T4 after ~75 min in the queue, installed in 90 s and loaded ACE-Step, but all three candidates failed in 19–58 s: `LanguageIdentifier has no attribute 'from_pickled_model'`. Unpinning dependencies for F14 pulled a newer `py3langid` whose API changed.
- **What broke (watcher):** the local Wan poller stopped printing at 301 s; `ps` showed one `kaggle kernels status` subprocess hung for 52 min.
- **What fixed it:** pinned `py3langid==0.3.0` (pure Python, fine on 3.13); `music.py` no longer stamps the cache unless every candidate exists, and exits non-zero when none were produced. Every Kaggle CLI call now has a timeout (120 s for status, 600 s for push/upload/download); I killed the hung call and the poller resumed.
- **Lesson:** "unpin everything" fixes one break and causes the next; pin what the code calls directly, relax only what blocks the install.

## F17: Laptop slept during the Kaggle jobs; downloads broke, not the jobs (2026-11-25)
- **What happened:** both pollers reported `error` after a ~2 h jump in their clocks (386 s → 7,247 s): the laptop had gone to sleep, and the download step failed with `Connection aborted`. Kaggle itself showed the music job **COMPLETE** (A 186.7 s, B 137.0 s, C 133.2 s on a T4, setup 87.6 s) and the Wan job still **QUEUED**.
- **What fixed it:** downloaded the music outputs again (`kaggle kernels output`), logged the three generations to runs.jsonl from `timings.json`, stamped the cache; re-attached a watcher to the queued Wan job with `--resume`.
- **Lesson:** a remote job's status and the local poller's status are different things; check the remote state before re-running anything.

## F18: Watcher reported a queued job as "error"
- **What happened:** after the laptop woke from sleep, the Wan watcher stopped with "ended with status error",
  but Kaggle still showed the job as QUEUED.
- **Cause:** the status call returned a network error message. The poller looked for the word "error"
  anywhere in the output, so it mistook the connection failure for a failed job.
- **Fix:** the poller now reads only Kaggle's `KernelWorkerStatus.<X>` field. Any other output counts as
  "status unavailable" and is retried. The watcher was re-attached with `--resume`, and the job was never lost.
