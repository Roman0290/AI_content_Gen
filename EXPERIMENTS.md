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
