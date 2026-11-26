# Costs

Everything ran on free tiers: **$0 spent**. The binding constraint was quota, not money. All numbers below
come from `runs.jsonl` (aggregate it with the snippet at the bottom).

## Free-tier quotas measured (2026-11-25)
| Provider | Quota | How we know | Resets |
|---|---|---|---|
| Gemini TTS (per model, per project) | **10 requests/day** | 429 `GenerateRequestsPerDayPerProjectPerModel-FreeTier`, quotaValue 10 (F06) | ~11:00 EAT |
| Gemini image models (flash-image, Nano Banana) | **0** on the free tier | immediate 429 on both keys (F12) | — |
| Cloudflare Workers AI (per account) | **10,000 neurons/day ≈ 15 FLUX.2 klein-9B images** at 720×1280 | 429 code 4006 (F07) | 00:00 UTC (03:00 EAT) |
| Gemini text (3.8 Flash) | not reached | 503 "high demand" (overload, not quota); fell back to 3.5 Flash | — |
| Kaggle GPU | ~30 h/week (brief) | music + Wan jobs below | weekly |

## Per-stage measurements
| Stage | Model | Calls (ok) | Mean latency | GPU min | List-price equivalent |
|---|---|---|---|---|---|
| Reference sheets | FLUX.2 klein 9B, 1280×720 | 3 | 11.6 s | 0 | ~650 neurons each ≈ $0.007 each at $0.011 / 1k neurons |
| Keyframes | FLUX.2 klein 9B, 720×1280, 1–2 reference images | 11 | 16.3 s | 0 | ≈ $0.08 for 11 (+4 blocked by quota) |
| Narration (main) | gemini-3.8-flash-tts | 11 | 17.5 s (incl. queueing; single calls 4–8 s) | 0 | see Gemini API pricing page for TTS; ~47 s of audio total |
| Narration (lite, discarded) | gemini-3.8-flash-lite-tts | 9 | 3.9 s | 0 | — (rejected by ear, E03) |
| Shots (fallback) | FFmpeg pan-and-zoom, local | 11 | ~5 s per shot | 0 | $0 |
| Shots (Wan 2.2) | Wan 2.2 TI2V-5B, 480×832, 49 frames, 25 steps, model CPU offload, Kaggle T4 | 9 | 474 s per clip (471.8–485.3 s), peak 12.96 GB VRAM, + 342 s setup | 76.9 (successful run) + ~7.5 (F19 run) + F13 run | ≈ $0.45 at T4 ≈ $0.35/h |
| Music | ACE-Step v1 3.5B, 3 × 77 s, 60 steps, Kaggle T4 | 3 | 152 s per candidate (A 186.7, B 137.0, C 133.2) + 87.6 s setup | ≈ 9.1 GPU min of generation (plus ~75 min in Kaggle's free queue) | ≈ $0.05 at T4 ≈ $0.35/h |
| Assembly | FFmpeg, local | — | ~2 min for both exports | 0 | $0 |

Failed or wasted calls are part of the cost: the Wan job queued ~14 h on account 2 and never started (switched accounts), and one 7.5 min run failed every shot on a device bug (F19); 12 narration calls failed on the daily quota (≈ 55 s each
before F06's fix stopped retrying daily quotas), 4 keyframe calls failed on the Cloudflare allocation.

## Experiments
| Experiment | Model | Calls | Mean latency |
|---|---|---|---|
| E02 Mom voice/direction | gemini-3.8-flash-tts | 8 ok, 3 rejected (system instruction) | 10.9 s |
| E02 transcription check | gemini-3.5-flash | 3 | 6.5 s |
| E03 emotion tags | gemini-3.1-flash-tts-preview | 6 | 7.6 s |

## Frontier comparison
Not available: no frontier-lane key was provided, and the Gemini image models return 0 free quota (F12).

## Reproduce these numbers
```bash
.venv/bin/python -c "import json,collections as c;a=c.defaultdict(list)
[a[(r['stage'],r['model'],r['status'])].append(r.get('latency_s') or 0) for r in map(json.loads,open('runs.jsonl'))]
[print(k,len(v),round(sum(v)/len(v),1)) for k,v in sorted(a.items())]"
```
