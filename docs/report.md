# The Heritage Short: report

**Film:** *If I Come and Find It (እኔ መጥቼ ካገኘሁት)*, 75 s, Amharic narration, English subtitles, 9:16 and 16:9.
**Repository:** <add GitHub link> · **Film links:** <add>

> Sections marked ✍️ need your own words and your testers' real answers. Everything else is drawn from the
> repository (runs.jsonl, EXPERIMENTS.md, FAILURES.md, DESIGN.md).

## 1. What I set out to make, and for whom
A short comedy-of-recognition about the Habesha mom, from two true moments in our house: Mom asks for her bag
from the bedroom table, I can't find it and shout so; she says *"እኔ መጥቼ ካገኘሁት…"* ("if I come and find
it..."), walks in angry and finds it on the bed in one second. And, busy cooking wot, when I ask where to put
the trash she snaps *"ራሴ ላይ አድርጊው!"* ("put it on my head!").

**Audience:** Ethiopian and Habesha viewers at home and in the diaspora, on their phones (TikTok, Instagram,
Telegram, family WhatsApp groups). **Intent:** they recognise their own mom, laugh at the memory, not at her
(in the moment it was not funny; she was really angry or busy), tag their siblings, and end feeling warm.

✍️ Why this story matters to me: ...

## 2. What I learned from my audience
- **My own first listen changed the story** (DESIGN.md): Mom had been written as playful and teasing; in real
  life she is angry in the moment and the laugh only comes when we remember. I rewrote shots 05, 07 and 11
  with real anger and sarcasm ("ምን?! የለም?!", "ይሄ ምንድነው?!"), added emotion tags for the TTS, and removed
  shot 08, which said this idea out loud instead of letting the tone carry it.
- I rejected the lite TTS voices as unnatural; the logs showed my ear matched the model split exactly (E03).
- ✍️ User test 1 (radio cut, ≥3 people): who, what they said, what changed.
- ✍️ User test 2 (final cut, ≥3 people): who, what they said, what changed.

## 3. The hardest problem and how I solved it
**Free-tier quotas, and finding out what they actually are.** Nothing tells you the remaining quota; you
find out from a 429. I measured them: Gemini TTS **10 requests per model per day** (F06), Cloudflare
**10,000 neurons/day ≈ 15 FLUX.2 klein-9B images** (F07), not the 50–170 images the brief estimated for
schnell. My first retry helper made it worse by backing off ~70 s per shot on a quota that resets in 20 h.
The fixes are now pipeline features: daily quotas are detected and not retried; Gemini keys rotate across
projects; the cache means an interrupted run resumes without repeating a single call; a failed shot keeps
its previous clip as a `stale` placeholder so the film always assembles; and when no new keyframes could be
made, the two wrong ones became cutaways reusing other shots' frames.

A close second was **F09**: a harsh noise at the end of every line. The 160 ms burst was identical in every
clip, so it couldn't be speech: Gemini TTS now returns a complete WAV with an AI-provenance metadata chunk,
and I had been playing that metadata as audio. I repaired all 11 clips from the bytes already on disk with no
new API calls, and now keep the raw files so the provenance label survives.

## 4. Suggested practices, tested honestly
**One that beat my instinct: a JSON contract between stages, with caching by input hash.** My instinct was
one script that does everything. With the contract, when the TTS quota ran out after shot 3, nothing was lost:
after adding a second key the next run regenerated exactly the 8 missing clips; a second run made 0 calls
(runs.jsonl). Editing one line regenerates one clip, which is the live demo.

**One that did not work as suggested: describing what you want in the prompt.** For speech, the Gemini TTS
model read my English directions aloud: one Amharic line became 28 s instead of 2.9 s (E02). For images,
"furious mom" still produced smiling faces (E04). What worked instead: sending only the line, carrying emotion
with Amharic punctuation and a short `[angry]` tag (E03), and writing images as visible actions ("mouth open
mid-shout", "view from behind").

Also tested: **a reference sheet before keyframes** worked well: Mom and the girl stay consistent across all
11 keyframes with no training (E04). And an AI judge is not a substitute for native listeners: Gemini
mistranscribed the Amharic clips while rating them 5/5 (E02).

## 5. Ceiling work
- Measured the real free-tier quotas and built quota-aware failure handling (daily-quota detection, key
  rotation, stale placeholders, time-budgeted GPU jobs).
- Found and documented that Gemini TTS embeds AI-provenance metadata in its WAV output; the pipeline preserves
  the raw files (F09, ETHICS.md).
- Tested whether an LLM can evaluate Amharic TTS: it cannot reliably (E02).
- ✍️ anything else you add (e.g. a second language, a blind test).

## 6. What I would build next
- A small web form where a relative tells their story in Amharic and gets a storyboard and radio cut back.
- Per-line voice acting: record Mom's lines with consent, or test more TTS models with native listeners.
- Train a small LoRA on the character sheets and measure whether emotions and consistency improve.
- ✍️ your own idea.
