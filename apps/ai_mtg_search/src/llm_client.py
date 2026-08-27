"""OpenAI-compatible chat client factory (Groq, HF, OpenAI, xAI)."""

from __future__ import annotations

from datetime import date

from langchain_openai import ChatOpenAI

from src.config import (
    LLM_BASE_URL,
    LLM_DAILY_REQUEST_CAP,
    LLM_MODEL,
    get_llm_api_key,
)

TEMPERATURE = 0.1
PLANNER_MAX_TOKENS = 1024
RANKER_MAX_TOKENS = 4096

# Process-local daily counter. Fine for a single Streamlit replica demo.
_request_day: date | None = None
_request_count = 0


class QuotaExceeded(Exception):
    """App-side or provider quota exhausted."""


class LlmNotConfigured(Exception):
    """No API key available for the chat LLM."""


def remaining_daily_requests() -> int | None:
    """None means no cap configured."""
    if LLM_DAILY_REQUEST_CAP <= 0:
        return None
    _roll_day()
    return max(0, LLM_DAILY_REQUEST_CAP - _request_count)


def _roll_day() -> None:
    global _request_day, _request_count
    today = date.today()
    if _request_day != today:
        _request_day = today
        _request_count = 0


def consume_llm_request() -> None:
    """Increment the daily counter or raise QuotaExceeded."""
    if LLM_DAILY_REQUEST_CAP <= 0:
        return
    global _request_count
    _roll_day()
    if _request_count >= LLM_DAILY_REQUEST_CAP:
        raise QuotaExceeded("Daily LLM request cap reached")
    _request_count += 1


def get_chat_llm(*, max_tokens: int | None = None, **kwargs) -> ChatOpenAI:
    """Build a ChatOpenAI pointed at whatever host LLM_BASE_URL names."""
    api_key = get_llm_api_key()
    if not api_key:
        raise LlmNotConfigured(
            "No LLM API key set. Add GROQ_API_KEY (or LLM_API_KEY) to .env "
            "or Streamlit secrets."
        )
    params: dict = {
        "model": LLM_MODEL,
        "api_key": api_key,
        "base_url": LLM_BASE_URL,
        "temperature": TEMPERATURE,
    }
    if max_tokens is not None:
        params["max_tokens"] = max_tokens
    params.update(kwargs)
    return ChatOpenAI(**params)


def is_quota_error(exc: BaseException) -> bool:
    """True for provider rate/credit errors or our own QuotaExceeded."""
    if isinstance(exc, QuotaExceeded):
        return True
    status = getattr(exc, "status_code", None) or getattr(exc, "http_status", None)
    if status in (402, 429):
        return True
    text = str(exc).lower()
    markers = (
        "rate limit",
        "429",
        "402",
        "quota",
        "insufficient",
        "credit",
        "too many requests",
        "resource_exhausted",
    )
    return any(m in text for m in markers)
