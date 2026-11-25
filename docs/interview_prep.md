# Interview prep: what to know about your own project

The interviewer checks that the repo reflects **your** understanding. Re-read FAILURES.md, EXPERIMENTS.md and
DESIGN.md before the call. Below: the likely questions, with the facts from this project. Answer in your own
words.

## 1. "Why is your pipeline shaped this way?"
- **One contract:** `storyboard.json`, validated by a JSON Schema before every run. Every stage reads it and
  writes its own folder + `manifest.json`. Stages never call each other, they only read manifests.
- **Stages:** reference sheets → keyframes → narration → shots → music → assemble (+ subtitles, radio cut).
- **Why narration before shots?** Amharic line length decides the shot length: a shot is
  `max(planned, narration + 0.6 s)`. Shot 09 grew from 7.0 to 7.25 s automatically.
- **Caching:** every file is named `<shot>_<hash>`; the hash covers model, prompt/text, voice, seed, size and
  the reference images. Same inputs → file exists → no API call. Change one line → one new call.
- **Timeline in one place** (`common/timeline.py`): subtitles and audio use the same start times, so they
  can't drift.

## 2. "Walk me through one experiment" (pick one, know the numbers)
**E02: why Mom's lines were 10–29 s long.**
- Hypothesis: a rich English "director's note" makes Mom sound natural.
- Result: the TTS model **read the directions aloud**: 28–29 s with the long note, 17 s with an Amharic note,
  9 s with one sentence, **2.9 s with only the Amharic line**.
- I also found Gemini can't judge Amharic: its transcription was wrong while rating pronunciation 5/5.
- Decision: send only the line; tone comes from punctuation and voice choice, and native listeners judge it.

**E03: main vs lite TTS + emotion tags.** I said shots 5–7 sounded unnatural; the manifest showed exactly
those came from the lite fallback model. Decision: main model only. Then `[angry] line` tags tested on another
model: tagged clips were not longer (5.80 vs 6.18 s), so the tag is not spoken.

**E04: reference sheets for consistency.** Character sheets passed as input images to FLUX.2 klein kept Mom
and the girl identical across 11 keyframes, but emotions were often wrong (Mom smiling while scolding).

## 3. "Describe a failure and what you did" (pick one)
- **F09, the noise at the end of every line (best story):** I heard a harsh sound at each shot end. Measured:
  last 160 ms at full scale, identical in every clip, so not speech. Cause: Gemini TTS now returns a whole WAV
  file with an AI-provenance metadata chunk; my code wrapped it as raw audio and played the metadata as sound.
  Fix: parse the WAV, keep the raw file (preserves the AI label), repaired 11 clips with **zero new API calls**.
- **F06, TTS quota is 10 requests/day per model:** my retry helper waited ~70 s per shot on a quota that
  resets in 20 h. Fix: detect daily quotas and don't retry; key rotation to a second project's key (F08).
- **F07, Cloudflare ran out after ~15 images** (10,000 neurons/day; klein-9B costs ~650 per image, not the
  50–170 images the brief estimated). Fix: the 2 wrong keyframes became cutaways reusing shots 06 and 09.
- **F02, TTS rejected `speechConfig`:** the SDK used the stable `v1` API; TTS only exists on `v1beta`.

## 4. "What did your audience tell you, and what changed?"
- Your own review as a native listener already changed the storyboard (DESIGN.md table):
  - Mom must be **really angry** in the moment ("we only laugh when we remember"): shot 05 got "ምን?! የለም?!",
    shot 07 got "ይሄ ምንድነው?!", shot 11 is sarcastic; emotion tags added.
  - Shot 08 removed: it said the idea out loud instead of letting the tone carry it.
  - Lite TTS voices rejected → main model only.
- **TODO before the interview:** fill DESIGN.md with what your 3+ radio-cut testers and 3+ final-cut testers
  actually said, and what you changed. Know two quotes by heart.

## 5. "Which suggested practice helped, which didn't?"
- **Helped: the JSON contract + caching.** When the quota ran out mid-run, nothing was lost; the next day /
  next key only regenerated the missing shots. Live shot regeneration is one command.
- **Helped: reference sheet before keyframes.** Consistency across 11 shots without training anything.
- **Didn't work as expected: "describe the style/emotion in the prompt".** For TTS the model spoke the
  directions; for images, "angry" still produced smiling faces. Strong visible actions ("mouth open
  mid-shout", "view from behind") and short tags worked better.
- **Mixed: logging every call.** It's how F09, E03 and the quota numbers were found, but also showed that an
  AI judge can't evaluate Amharic.

## 6. Numbers to remember
- Film: 11 shots, 75 s (72 s + 3 s end card), 47 s of speech; 720×1280 and 1280×720; −16 LUFS target.
- Quotas: Gemini TTS 10/day/model/project; Cloudflare 10,000 neurons/day ≈ 15 klein-9B images; Kaggle ~30 GPU h/week.
- Latency: TTS ~4–8 s per line; FLUX.2 klein ~8 s per image; Wan and ACE-Step: see COSTS.md (GPU minutes).
- Cost: $0.

## 7. Live demo for the walkthrough
1. Change `shots[shot_10].narration` (or `image_prompt`) in `storyboard.json`.
2. `make film` → only `shot_10` says `[new]`, everything else `[cached]`.
3. `tail -1 runs.jsonl` → the single new model call.
(Keep 2 TTS calls of daily quota free for this.)
