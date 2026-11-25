"""Shared Gemini client and TTS helper."""
import os
import wave
from pathlib import Path

from .config import env

TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-3.8-flash")
TEXT_FALLBACK = os.getenv("GEMINI_TEXT_FALLBACK", "gemini-3.5-flash")
TTS_MODEL = os.getenv("GEMINI_TTS_MODEL", "gemini-3.8-flash-tts")
TTS_FALLBACK = os.getenv("GEMINI_TTS_FALLBACK", "gemini-3.8-flash-lite-tts")
TTS_RATE = 24000  # Gemini TTS returns 24 kHz, 16-bit, mono PCM

_client = None
_key_idx = 0


def _keys() -> list[str]:
    """GEMINI_API_KEY, then GEMINI_API_KEY2 / GEMINI_API_KEY_2, ... (each from a separate project, F08)."""
    keys = [env("GEMINI_API_KEY")]
    for n in range(2, 10):
        k = os.getenv(f"GEMINI_API_KEY{n}") or os.getenv(f"GEMINI_API_KEY_{n}")
        if k and k not in keys:
            keys.append(k)
    return keys


def key_index() -> int:
    """Which key is in use (logged instead of the key itself)."""
    return _key_idx


def next_key() -> bool:
    """Switch to the next API key after a daily quota error. False if there is none left."""
    global _key_idx, _client
    if _key_idx + 1 >= len(_keys()):
        return False
    _key_idx += 1
    _client = None
    return True


def client():
    """One shared client. v1beta: TTS models and speech_config are not exposed on the stable v1 API (F02)."""
    global _client
    if _client is None:
        from google import genai
        from google.genai import types

        _client = genai.Client(api_key=_keys()[_key_idx], http_options=types.HttpOptions(api_version="v1beta"))
    return _client


def split_wav(data: bytes) -> tuple[bytes, int]:
    """Gemini TTS may return a complete WAV (RIFF header + PCM + a provenance metadata chunk) or bare PCM.
    Return (pcm, sample_rate). Treating the WAV bytes as PCM plays the header as a click and the
    metadata as a 160 ms noise burst at the end of every line (F09)."""
    import io

    if data[:4] == b"RIFF":
        with wave.open(io.BytesIO(data)) as w:
            return w.readframes(w.getnframes()), w.getframerate()
    return data, TTS_RATE


def tts_wav_bytes(text: str, voice: str, model: str = TTS_MODEL) -> bytes:
    """Raw TTS response bytes (kept on disk as-is so the provenance metadata survives)."""
    return _tts(text, voice, model)


def tts_pcm(text: str, voice: str, model: str = TTS_MODEL) -> bytes:
    """Clean PCM at TTS_RATE for `text`."""
    pcm, _ = split_wav(_tts(text, voice, model))
    return pcm


def _tts(text: str, voice: str, model: str) -> bytes:
    """Speak `text` exactly. No style direction is sent: the model reads directions aloud (E02)."""
    from google.genai import types

    resp = client().models.generate_content(
        model=model,
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice))
            ),
        ),
    )
    return resp.candidates[0].content.parts[0].inline_data.data


def write_wav(path: Path, pcm: bytes, rate: int = TTS_RATE) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
