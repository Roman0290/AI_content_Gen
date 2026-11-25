"""Cloudflare Workers AI image generation (FLUX)."""
import base64
import os
from pathlib import Path

import requests

from .config import env

IMAGE_MODEL = os.getenv("CF_IMAGE_MODEL", "@cf/black-forest-labs/flux-2-klein-9b")


def generate_image(prompt: str, width: int, height: int, seed: int | None = None,
                   refs: list[Path] = (), model: str = IMAGE_MODEL) -> bytes:
    """FLUX.2 models take multipart form data; up to 4 reference images as input_image_0..3."""
    url = f"https://api.cloudflare.com/client/v4/accounts/{env('CF_ACCOUNT_ID')}/ai/run/{model}"
    headers = {"Authorization": f"Bearer {env('CF_API_TOKEN')}"}
    if "flux-2" in model:
        files = {"prompt": (None, prompt), "width": (None, str(width)), "height": (None, str(height))}
        if seed is not None:
            files["seed"] = (None, str(seed))
        for i, ref in enumerate(refs[:4]):
            files[f"input_image_{i}"] = (ref.name, ref.read_bytes(), "image/png")
        r = requests.post(url, headers=headers, files=files, timeout=180)
    else:  # flux-1-schnell: JSON, no seed, no references (F03)
        r = requests.post(url, headers=headers, json={"prompt": prompt, "steps": 4}, timeout=180)
    r.raise_for_status()
    return base64.b64decode(r.json()["result"]["image"])
