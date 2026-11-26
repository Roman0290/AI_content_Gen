# Experiments

<!-- Template:
## E01: title
- **Hypothesis:**
- **Change:**
- **Result:** (cite runs.jsonl lines / outputs)
- **Decision:**
-->

## E01: Does FLUX know what a jebena is? (2026-11-25)
- **Hypothesis:** naming "jebena coffee pot" is enough for FLUX.1 schnell to draw an Ethiopian clay jebena.
- **Change:** smoke-test prompt "...Ethiopian living room, jebena coffee pot on a low table..." (`outputs/smoke/image_flux.jpg`).
- **Result:** warm hand-painted style came out well, but the pot was a metal Arabic dallah, not a black clay jebena. No sini cups, no incense.
- **Decision:** describe culturally specific objects by shape and material ("round-bellied black clay coffee pot with a long thin neck and straw stopper") instead of relying on the Amharic name. Apply to all storyboard prompts.

## E02: Making Mom sound natural, and why Amharic lines ran long (2026-11-25)
- **Hypothesis:** a rich English "director's note" (who she is, the scene, the mood) in the TTS prompt makes Mom's line sound like a real Habesha mom.
- **Change:** `scripts/experiments/tts_mom_voice.py`, line "እኔ መጥቼ ካገኘሁት እረግጥሻለሁ!", 11 variants (voices Kore/Sulafat/Gacrux; direction in prompt, as a system instruction, as a short prefix, or none). Results in `outputs/experiments/tts_mom/` and runs.jsonl (`stage: exp_tts_mom`).
- **Result:**
  | Variant | Direction | Audio length |
  |---|---|---|
  | A–C (3 voices) | long English scene in prompt | 28.4–29.2 s |
  | D | long Amharic direction in prompt | 17.0 s |
  | E–G | system instruction | 400 "Developer instruction is not enabled for this model" |
  | H–I | one-sentence English prefix | 9.1–9.5 s |
  | J | none | **2.9 s** |
  | K | none, Amharic punctuation + "ዋ!" | **3.2 s** |
  The model speaks (part of) the direction aloud; the extra seconds were never the Amharic line itself. The 9.8 s smoke-test clip had the same cause.
- **Side finding:** gemini-3.5-flash transcriptions of the clips were wrong ("እኔም ጥሩ አግኝቼው ረክቻለሁ" for J) while rating the pronunciation 5/5. An AI judge cannot evaluate Amharic speech here; a native listener must.
- **Decision:** send only the Amharic line to TTS; shape tone with Amharic punctuation and interjections (፣ ! ዋ!) and voice choice. Mom's delivery is judged by ear by native listeners in user test 1.

## E03: Main vs lite TTS model, and emotion tags for Mom (2026-11-25)
- **Observation that started it:** a native listener (me) found shots 5, 6, 7 "not natural" but liked shots 1–3. `outputs/narration/manifest.json` shows 1–3 were made by gemini-3.8-flash-tts and 4–12 by the fallback gemini-3.8-flash-lite-tts (F06).
- **Hypothesis 1:** the lite model is the cause, not the voice or the text.
- **Result 1:** the split between "natural" and "not natural" matches the model split exactly. **Decision:** narration uses only the main model; fallback is opt-in (`--allow-fallback`) and clips made by another model are treated as stale and regenerated when the quota resets (Thu 26 Nov ~11:00 EAT). 8 clips × 1 call = 8 of the 10 daily calls.
- **Hypothesis 2:** a short bracketed tag (`[angry] line`) changes the emotion without being read aloud, unlike the long directions in E02.
- **Change:** `scripts/experiments/tts_emotion_tags.py` on gemini-3.1-flash-tts-preview (separate quota), shots 05, 07, 11, plain vs tagged.
- **Result 2:**
  | Shot | Tag | Plain | Tagged |
  |---|---|---|---|
  | 05 | angry | 6.18 s | 5.80 s |
  | 07 | angry | 3.12 s | 2.83 s |
  | 11 | sarcastic, annoyed | 1.28 s | 1.44 s |
  Tagged clips are not longer, so the tag is not spoken (E02 directions added 6–26 s). Whether the emotion is right is judged by ear.
- **Decision:** `tts_tag` field in the storyboard (angry for 05 and 07, sarcastic/annoyed for 11), sent as `[tag] line`, never shown in subtitles.

## E04: FLUX.2 klein 9B with reference sheets for character consistency (2026-11-25)
- **Hypothesis:** generating a character sheet first and passing it as an input image to every keyframe keeps Mom and the girl recognisably the same person across shots (text descriptions alone would drift).
- **Change:** `pipeline/reference.py` (3 sheets: mom, child, daughter_adult based on child), `pipeline/keyframes.py` passes each shot's characters' sheets as `input_image_0..3` on `@cf/black-forest-labs/flux-2-klein-9b`, 720×1280, fixed seeds. ~7.6 s per image.
- **Result:** across all 11 keyframes Mom keeps the same headwrap with tilet border, cream dress, gold cross and face; the girl keeps the hair puffs with yellow ribbons, striped t-shirt and grey skirt. Contact sheet: `outputs/keyframes/contact_sheet.jpg`. The jebena described by shape (E01) now renders as a black clay pot.
- **Failures in the same batch:** emotion was often wrong: shot 07 Mom smiling instead of scolding, shot 11 facing the camera and smiling instead of turned away, shot 03 girl smiling while searching; shot 05 included a blonde non-Ethiopian guest. The adult daughter sheet kept the child's hair puffs in the close-up.
- **Decision:** keep the reference-sheet approach. Write emotions as strong visible actions ("furious, mouth open mid-shout", "view from behind") and say the guests are Ethiopian. Re-run of shots 03/05/07/11 blocked by F07.

## E05: Choosing the score from three ACE-Step candidates (2026-11-25)
- **Hypothesis:** the genre of the score changes how the film reads. A playful track makes Mom a joke; a
  nostalgic one makes the film a memory, which is the intended tone ("we laugh when we remember", without
  saying it in the story).
- **Change:** the same storyboard generated three 77 s instrumentals with ACE-Step v1 on a Kaggle T4, with fixed
  seeds: **A** playful krar/masinko/kebero at 100 bpm (seed 11), **B** tizita, warm and nostalgic at 80 bpm
  (seed 22), **C** lively eskista in 6/8 at 110 bpm (seed 33). Each was mixed under the narration with the
  same sidechain ducking.
- **Result:** chosen **B (tizita)** after listening to all three. ✍️ Reason, in your own words: ...
- **Decision:** `storyboard.json` → `music.chosen: "B"`; `make film` copies it to `outputs/music/chosen.wav`.
  Both exports measure **−16.8 LUFS** integrated (target −16).

## E06: Can Gemini TTS say the Amharic ejective ch' (ጨ family) in Mom's first line? (2026-11-26)
- **Hypothesis:** user test 2 (Person 1) heard Mom mispronounce ch' in "አምጪልኝ" (shot_02). If it was a
  one-off bad sample, a plain retake fixes it. If the model can't produce the sound, only a rephrase that
  avoids the sound fixes it.
- **Change:** `scripts/experiments/tts_ejective_retake.py`, same model (gemini-3.8-flash-tts) and voice (Kore),
  three takes against the current clip: **A** the same line again, **B** the line with a
  `[clear, careful pronunciation]` tag, **C** a rephrase without the sound ("ይዘሽልኝ ነይ", "bring it to me").
  Outputs in `outputs/experiments/e06_ch_sound/`. runs.jsonl `stage: experiment_e06`: 3 ok (5.8 s, 5.9 s,
  3.1 s), 2 hit the daily quota on key 1 and went through on key 2 (F06).
- **Result (measured):** durations: current 3.13 s, A 3.58 s, **B 6.10 s**, C 3.77 s. In E03 an emotion
  tag did not change the length (it was not spoken). Here the tag almost doubles it. That suggests a
  long, instruction-like tag is partly read aloud or slows the whole delivery, so B is suspect before
  anyone listens. ✍️ Which take a native listener chose, and whether A still has the wrong ch'.
- **Decision:** ✍️ (storyboard shot_02 still has the original line "…አምጪልኝ።"). Lesson either way: a
  tester's pronunciation complaint is cheap to test with three takes (about 15 s of API time). Rephrasing
  around a sound the model can't make is a valid fix for a narration you control.

## E07: Does Wan 2.2 image-to-video keep the characters' identity? (2026-11-26)
- **Hypothesis:** image-to-video holds the keyframe's identity for the whole clip, because the first frame
  is fixed (Appendix B: "image-to-video is much more consistent than text-to-video").
- **Change:** none to generation. User test 2 (Person 2: "the animation changes people's appearance a little")
  prompted a check of the first and last frame of all 9 clips from the first successful Wan run
  (runs.jsonl 2026-11-26T05:39, seeds 101–112, 480×832, 49 frames, 25 steps).
- **Result:** 4 of 9 clips drifted, and every one of them had an action motion prompt: shot_01 (relatives
  laughing): people rearrange and a new man appears. shot_03 (fast search, clothes tossed): the girl
  turns into a different child. shot_04 (girl shouts, camera shake): her face distorts. shot_05 (Mom rises
  and walks): she walks out of frame during her own angry line. The 5 that held (02, 06, 09, 10, 12) had
  small motions (a gesture, steam, a head tilt, a slow pull-out).
- **Decision:** the hypothesis is only half true. The first frame is fixed, but identity is not held
  after it. Interim fix: `"animate": false` on the 4 drifting shots (pan over the keyframe). Then E09
  tested whether the prompt, not the model, was the cause.

## E08: Why the Wan shots looked "dead": fitting 2 s clips into 5–8 s shots (2026-11-26)
- **Hypothesis:** Person 3's "work on the animation part" is not about motion quality. Each Wan clip is
  49 frames at 24 fps (2.04 s, confirmed with ffprobe on `outputs/shots/wan/*.mp4`), but the shots are
  5–8 s. The old `render_wan` slowed a clip by at most 1.5× and then held the last frame (`tpad
  stop_mode=clone`), so most of each shot is a still frame.
- **Change:** `pipeline/shots.py` `render_wan` now plays the clip and then continues from its last frame
  with a slow camera push-in (`pan_filter("slow push-in", …)`) for the rest of the shot. The cache key
  changed to `shot-v2`, so only the Wan shots re-rendered.
- **Result (measured, `ffmpeg -vf freezedetect=n=-50dB:d=0.5`):** old renders (2026-11-26 08:39): all 9
  Wan shots freeze from 2.92–3.00 s to the end, **34.2 s frozen out of the 72 s film**. Current renders
  (`outputs/shots/manifest.json`): **0 s frozen** in all 11 shots.
- **Decision:** keep the push-in tail. Lesson: measure before regenerating. The fix was a free FFmpeg
  change, not more GPU time. A 4× longer clip (81+ frames) would have run out of memory on the T4 (F13).

## E09: Calm motion prompts versus action motion prompts on the same seeds (2026-11-26)
- **Hypothesis:** the drift in E07 comes from asking for big actions. A video-only prompt that asks for
  almost nothing (breathe, blink, one gesture, "stays in place", "camera static") keeps identity, with
  the same keyframe and seed.
- **Change:** a new storyboard field `wan_motion_prompt` (only the Wan stage reads it; `motion_prompt` still
  drives the pan fallback), set on the 4 drifting shots, e.g. shot_03 "fast comic pan… clothes tossed in
  the air" became "the girl stays kneeling in the same place and slowly turns her head… Camera static".
  "Boy" was also fixed to "girl" in two motion prompts. Same seeds as E07 (101, 103, 104, 105); only the
  prompt changed. runs.jsonl 2026-11-26T08:34: 4 clips, 451–463 s each on a T4, peak 12.96 GB.
- **Result:** shot_01 and shot_03 now stable for the whole clip (kept, animated again). shot_04 and shot_05
  are good for about the first second, then the faces melt anyway.
- **Decision:** calm prompts fixed 2 of 4. Prompt wording matters, but it doesn't fully fix drift on
  faces with strong expressions (the girl's hands on her cheeks, Mom shouting). Combined with E07:
  **the more a prompt asks for, the more Wan 2.2 TI2V-5B drifts.** Calm motions (06, 10, 12) held in
  both runs.

## E10: Using only the good first second of a drifting clip (2026-11-26)
- **Hypothesis:** for shot_04 and shot_05 (E09), 1 s of real motion followed by a camera move looks better
  than a pan over a still, and hides the melt.
- **Change:** a new storyboard field `wan_use_s: 1.0`. `render_wan` trims the clip to that length, then continues
  with the push-in from that frame (E08). It is part of the shot's cache key, so changing it re-renders
  only that shot.
- **Result:** both shots render with no frozen frames (E08 measurement). The melting part is never shown.
  The film now has 9 animated shots + 2 cutaways (07, 11; F12), up from 5 Wan + 6 pan after E07.
- **Decision:** keep. This follows Appendix B's "if a clip is about 80 % right, trim it": no extra GPU time,
  and a storyboard field records the choice so a re-run reproduces it.

## E11: Fitting Wan 2.2 TI2V-5B on a 16 GB T4 (2026-11-25 → 26)
- **Hypothesis:** whole-model CPU offload at 81 frames is enough on a T4 (it is enough on a 24 GB card).
- **Change:** run 1: 480×832, 81 frames, fp16, `enable_model_cpu_offload` → run 2/3: 49 frames, VAE
  tiling, text embeddings computed first and the text encoder freed, a fallback chain of memory strategies,
  and stop after 2 identical errors.
- **Result:** run 1 (2026-11-25T13:33): OOM on the first shot at 14.39/14.56 GB, 0/9 clips (F13). Run 2
  (2026-11-26T04:16): no OOM, but 0/9 because of a CPU/CUDA device mismatch (F19). Run 3 (05:39): **9/9 clips,
  471.8–485.3 s each, peak 12.96 GB**, 76.9 GPU min.
- **Decision:** 49 frames at 480×832 is the working point on a free T4: ~1 GB of headroom, about 8 min per
  2 s clip. That budget is what made E08 (stretch with FFmpeg rather than generate longer clips) the
  right fix.
