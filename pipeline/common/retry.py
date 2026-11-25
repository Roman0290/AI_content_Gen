"""Retry with exponential backoff, only for transient errors (rate limits, overload, server errors).
Client mistakes (400/401/404) fail immediately so they are fixed rather than retried."""
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

TRANSIENT = {408, 429, 500, 502, 503, 504}


def _status(exc: BaseException):
    code = getattr(exc, "code", None)  # google-genai APIError
    if code is None and getattr(exc, "response", None) is not None:  # requests HTTPError
        code = getattr(exc.response, "status_code", None)
    return code


def is_daily_quota(exc: BaseException) -> bool:
    """A per-day free-tier quota will not recover within a retry window (F06)."""
    text = str(exc)
    resp = getattr(exc, "response", None)
    if resp is not None:
        text += getattr(resp, "text", "")
    # Gemini: quotaId ...PerDay...; Cloudflare Workers AI: code 4006 "daily free allocation" (F07)
    return _status(exc) == 429 and ("PerDay" in text or "daily free allocation" in text)


def is_transient(exc: BaseException) -> bool:
    if is_daily_quota(exc):
        return False
    return _status(exc) in TRANSIENT or isinstance(exc, (TimeoutError, ConnectionError))


with_retry = retry(
    retry=retry_if_exception(is_transient),
    stop=stop_after_attempt(6),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    reraise=True,
)
