"""Kaggle GPU job: animate keyframes with Wan 2.2 TI2V-5B (Apache 2.0) via diffusers, on a 14.5 GB T4.

Memory plan (run 1 ran out of GPU memory, F13):
  1. Text first, alone: load only the umT5 text encoder, encode every prompt once, keep the embeddings on CPU,
     then delete the encoder. The video model never shares memory with it (GPU or RAM).
  2. Load the pipeline WITHOUT the text encoder (fp16 transformer, fp32 VAE with tiling).
  3. Strategy ladder per run: model CPU offload (fast) -> on CUDA OOM, sequential CPU offload (layers streamed
     one at a time, slow but small) and retry the same shot.
  4. After any failure: free memory; stop after 2 OOMs in a row; stop starting new shots after BUDGET_MIN.
Input: dataset with keyframes + jobs.json. Output: /kaggle/working/<out_name>.mp4, timings.json, progress.log.
"""
import gc
import glob
import json
import os
import subprocess
import sys
import time

T0 = time.time()
LOG = open("/kaggle/working/progress.log", "a")


def log(*a):
    msg = f"[{time.time() - T0:7.1f}s] " + " ".join(str(x) for x in a)
    print(msg, flush=True)
    LOG.write(msg + "\n")
    LOG.flush()


# Preflight (F15): an unverified Kaggle account silently gets no internet; fail in seconds, not after setup.
import socket  # noqa: E402

try:
    socket.create_connection(("pypi.org", 443), timeout=10).close()
    socket.create_connection(("huggingface.co", 443), timeout=10).close()
except OSError as e:
    sys.exit(f"PREFLIGHT FAILED: no internet ({e}). Phone-verify the Kaggle account and enable Internet.")
if subprocess.run(["nvidia-smi"], capture_output=True).returncode != 0:
    sys.exit("PREFLIGHT FAILED: no GPU in this session.")
log("preflight ok: internet + GPU")

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "diffusers", "transformers", "accelerate",
                "ftfy", "imageio", "imageio-ffmpeg"], check=True)

import html  # noqa: E402
import re  # noqa: E402

import ftfy  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402
from diffusers import AutoencoderKLWan, WanImageToVideoPipeline  # noqa: E402
from diffusers.utils import export_to_video, load_image  # noqa: E402
from transformers import AutoTokenizer, UMT5EncoderModel  # noqa: E402

MODEL = "Wan-AI/Wan2.2-TI2V-5B-Diffusers"
jobs_path = glob.glob("/kaggle/input/**/jobs.json", recursive=True)[0]
IN = os.path.dirname(jobs_path)
cfg = json.load(open(jobs_path))
W, H, FRAMES, STEPS, BUDGET = cfg["width"], cfg["height"], cfg["frames"], cfg["steps"], cfg["budget_min"]
NEG = ("static, still image, blurry, distorted face, extra fingers, deformed hands, text, watermark, subtitles, "
       "low quality, jpeg artifacts, flicker")
MAXLEN = 512
FP = torch.float16  # T4 (compute 7.5) has no fast bf16
timings = {"gpu": torch.cuda.get_device_name(0), "gpus": torch.cuda.device_count(),
           "vram_gb": round(torch.cuda.get_device_properties(0).total_memory / 2**30, 1),
           "width": W, "height": H, "frames": FRAMES, "steps": STEPS, "jobs": []}
log("start", timings)


def free():
    gc.collect()
    torch.cuda.empty_cache()


def save_timings():
    json.dump(timings, open("/kaggle/working/timings.json", "w"), indent=2)


# ---- 1. text embeddings, with the text encoder alone -------------------------------------------------------
def clean(t):
    return re.sub(r"\s+", " ", html.unescape(html.unescape(ftfy.fix_text(t)))).strip()


def encode(texts, te, tok, device):
    ti = tok([clean(t) for t in texts], padding="max_length", max_length=MAXLEN, truncation=True,
             add_special_tokens=True, return_attention_mask=True, return_tensors="pt")
    lens = ti.attention_mask.gt(0).sum(dim=1).long()
    with torch.no_grad():
        e = te(ti.input_ids.to(device), ti.attention_mask.to(device)).last_hidden_state.float().cpu()
    return torch.stack([torch.cat([u[:v], u.new_zeros(MAXLEN - v, u.size(1))]) for u, v in zip(e, lens)])


t = time.time()
tok = AutoTokenizer.from_pretrained(MODEL, subfolder="tokenizer")
texts = [j["prompt"] for j in cfg["jobs"]] + [NEG]
te = UMT5EncoderModel.from_pretrained(MODEL, subfolder="text_encoder", torch_dtype=FP).to("cuda")
emb = encode(texts, te, tok, "cuda")
te_mode = "gpu fp16"
if not torch.isfinite(emb).all():  # T5 overflows in fp16 on some inputs: redo on CPU in bf16
    log("fp16 text embeddings not finite -> CPU bf16")
    te = te.to("cpu", torch.bfloat16)
    free()
    emb = encode(texts, te, tok, "cpu")
    te_mode = "cpu bf16"
del te
free()
NEG_EMB = emb[-1:].to(FP)
PROMPT_EMB = {j["shot"]: emb[i:i + 1].to(FP) for i, j in enumerate(cfg["jobs"])}
timings["text"] = {"mode": te_mode, "seconds": round(time.time() - t, 1), "finite": bool(torch.isfinite(emb).all())}
log("text embeddings", timings["text"])
save_timings()

# ---- 2. video pipeline without the text encoder ------------------------------------------------------------
t = time.time()
vae = AutoencoderKLWan.from_pretrained(MODEL, subfolder="vae", torch_dtype=torch.float32)
try:
    pipe = WanImageToVideoPipeline.from_pretrained(MODEL, vae=vae, text_encoder=None, tokenizer=None, torch_dtype=FP)
except Exception as e:  # older/newer diffusers may refuse None components: load, then drop the encoder
    log("load without text encoder failed, fallback:", repr(e)[:200])
    pipe = WanImageToVideoPipeline.from_pretrained(MODEL, vae=vae, torch_dtype=FP)
    pipe.text_encoder = None
    free()
pipe.vae.enable_tiling()
pipe.set_progress_bar_config(disable=True)
timings["load_s"] = round(time.time() - t, 1)

STRATEGIES = ["model_offload", "sequential_offload"]
strategy_idx = 0


def apply_strategy(i):
    try:
        pipe.remove_all_hooks()
    except Exception:
        pass
    pipe.to("cpu")
    free()
    if STRATEGIES[i] == "model_offload":
        pipe.enable_model_cpu_offload()
    else:
        pipe.enable_sequential_cpu_offload()
    log("memory strategy:", STRATEGIES[i])


apply_strategy(strategy_idx)
timings["setup_s"] = round(time.time() - T0, 1)
save_timings()


def step_log(p, i, ts, kw):
    if i % 5 == 0:
        log(f"  step {i}/{STEPS} peak {torch.cuda.max_memory_allocated() / 2**30:.1f} GB")
    return kw


# ---- 3. shots ---------------------------------------------------------------------------------------------
oom_in_a_row = 0
for job in cfg["jobs"]:
    if oom_in_a_row >= 2:
        timings["jobs"].append({**job, "status": "skipped: repeated out-of-memory"})
        continue
    if (time.time() - T0) / 60 > BUDGET:
        timings["jobs"].append({**job, "status": "skipped: time budget"})
        continue
    image = load_image(os.path.join(IN, job["keyframe"])).resize((W, H))
    while True:
        s = time.time()
        torch.cuda.reset_peak_memory_stats()
        frames = None
        try:
            log("shot", job["shot"], "with", STRATEGIES[strategy_idx])
            frames = pipe(image=image, prompt_embeds=PROMPT_EMB[job["shot"]], negative_prompt_embeds=NEG_EMB,
                          height=H, width=W, num_frames=FRAMES, num_inference_steps=STEPS, guidance_scale=5.0,
                          generator=torch.Generator("cpu").manual_seed(job["seed"]),
                          callback_on_step_end=step_log).frames[0]
            mid = np.asarray(frames[len(frames) // 2], dtype=np.float32)
            scale = 255.0 if mid.max() > 1.5 else 1.0
            ok = np.isfinite(mid).all() and mid.mean() / scale > 0.02  # fp16 overflow -> black/NaN frames
            export_to_video(frames, f"/kaggle/working/{job['out_name']}.mp4", fps=24)
            status = "ok" if ok else f"suspect: mean {mid.mean() / scale:.3f}"
            oom_in_a_row = 0
        except torch.cuda.OutOfMemoryError as e:
            frames = None
            free()
            if strategy_idx + 1 < len(STRATEGIES):  # smaller footprint, same shot again
                strategy_idx += 1
                apply_strategy(strategy_idx)
                continue
            status = f"error: {e!r}"[:300]
            oom_in_a_row += 1
        except Exception as e:
            frames = None
            free()
            status = f"error: {e!r}"[:300]
        break
    rec = {**job, "status": status, "strategy": STRATEGIES[strategy_idx], "seconds": round(time.time() - s, 1),
           "peak_gb": round(torch.cuda.max_memory_allocated() / 2**30, 2)}
    rec.pop("prompt", None)
    timings["jobs"].append(rec)
    log(job["shot"], status, rec["seconds"], "s", rec["peak_gb"], "GB")
    free()
    save_timings()
timings["total_min"] = round((time.time() - T0) / 60, 1)
save_timings()
log("done", timings["total_min"], "min")
