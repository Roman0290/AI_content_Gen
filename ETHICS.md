# Ethics

## Consent records
| Person | Shown / voiced | Consent (date, how, what they agreed to) |
|---|---|---|
| My mother (the story is from our house) | **Not shown, not voiced.** Mom is an illustrated character generated from a text description, not from a photo; her voice is a stock Gemini TTS voice (Kore). | TODO (fill in before posting): date, how she agreed (in person / phone), and that she is fine with the story being told publicly |
| Me / my siblings (the child) | **Not shown, not voiced.** The girl is an illustrated character; stock voice (Leda). | — |

No photo, video or voice recording of a real person was used as input to any model. The words in Mom's
mouth are the phrases from our own family story, retold as a generic Habesha mom, not an imitation of a
specific person's voice or face. If a real likeness or voice is ever added, consent is recorded here first.

## Licences
| Model / asset | Used for | Licence / terms | Output use |
|---|---|---|---|
| Gemini 3.8 Flash TTS (+ 3.1 Flash TTS preview for one experiment) | narration | Gemini API Terms of Service (free tier) | Free-tier prompts may be used by Google to improve products, so no private family details were sent: only the film's lines |
| Gemini 3.5 Flash | smoke test translation, one transcription experiment | Gemini API ToS | as above |
| FLUX.2 [klein] 9B on Cloudflare Workers AI | reference sheets, keyframes | Black Forest Labs terms via Cloudflare (partner model, bfl.ai/legal/terms-of-service); Cloudflare Workers AI terms | Non-commercial heritage film. Verify BFL terms before any commercial use |
| FLUX.1 [schnell] on Cloudflare | smoke test image | Apache 2.0 | unrestricted |
| Wan 2.2 TI2V-5B (open weights, Kaggle) | moving shots | Apache 2.0 | unrestricted |
| ACE-Step v1 3.5B (open weights, Kaggle) | score | Apache 2.0; ACE-Step states outputs may be used commercially | unrestricted |
| Noto Sans Ethiopic | subtitles, end card | SIL Open Font License 1.1 | unrestricted |
| FFmpeg | assembly | LGPL/GPL (local tool) | — |

## Labelling plan
- The film ends with a 3 s end card: **"Made with AI · ለእናቶቻችን"** (both aspect ratios).
- Posted with the platform's AI-content disclosure switched on (TikTok "AI-generated" label / YouTube
  "altered or synthetic content" / Meta "AI info").
- Gemini TTS embeds AI-provenance metadata in each WAV (`digitalsourcetype/trainedAlgorithmicMedia`, F09).
  The raw responses are kept unmodified as `outputs/narration/*.source.wav`; the metadata cannot survive
  mixing into the MP4, which is why the end card and platform label carry the disclosure.
- The post text says the images, voices and music are AI-generated.

## Style and identity
Style is described by qualities ("warm hand-painted 2D illustration, soft film grain, golden light"), never
by naming a living artist.

## Private data
Only the film's own lines and image descriptions were sent to hosted APIs. No names, addresses, photos or
other family details.
