"""Minimal OpenAI-compatible chat-completion client (Wave 6).

CONCURRENT-EDIT NOTE: during this task, a sibling agent ("Agent 27 — Deep
Model Benchmark Engineer") briefly overwrote this same file path with its own
stopgap implementation (a synchronous, non-raising `ok`/`error`-style
`chat_completion`), believing this file didn't exist yet. This version
restores the contract Agent 26's ("Fast Model Benchmark Engineer") task
explicitly specified — an **async** `chat_completion` returning a
`ChatCompletionResult(text, model, latency_ms, key_used, raw_usage)` and
**raising** a typed exception on total failure — since that is the exact
signature this wave's benchmark script and test suite are written against.
Per GLOBAL_ARCHITECTURE.md's "no second, competing X" rule, a later
integration pass should reconcile the two call-shapes into one canonical
client rather than leaving both agents' work colliding on one path; this
docstring exists so that reconciliation has context on why two shapes existed.

``model_pool.py`` (Wave 2) deliberately stops at "which key should the caller
use right now" — this module is the "later wave's job" it names: making the
actual HTTP call. See docs/assistant/NVIDIA_MODEL_RESEARCH.md for the target
provider (NVIDIA Build's OpenAI-compatible REST endpoint) and
docs/assistant/wave6/fast-model-benchmark.md for the empirical results this
client was built to produce.

Design constraints (AGENTS.md + GLOBAL_ARCHITECTURE.md):
  * The deterministic physics core is sacred — this module never computes a
    cardiac number, it only calls a remote chat model and hands back raw text.
    Callers are responsible for running the numeric-claim gate
    (``assistant.safety_validator.validate_numeric_claims``) and the output
    safety gate (``assistant.safety_validator.check_output_safety``) on
    whatever text comes back before treating it as safe to show a user.
  * Security invariant carried over from ``model_pool.py``: no function here
    ever returns, logs, or formats a raw key value. Callers get back a
    ``key_used`` string built only from the pool's slot index
    (e.g. ``"slot-2"``), matching ``KeyHandle.slot`` / ``get_pool_health()``'s
    own logging convention.
  * On total failure (no healthy key, or every attempted key's HTTP call
    fails) this raises a clear, typed exception rather than returning empty
    or fabricated text — callers must not silently treat a failed call as a
    successful empty response.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

import httpx

from python.hearttwin.assistant.model_pool import KeyHandle, ModelKeyPool

_DEFAULT_TIMEOUT_SECONDS = 30.0
_CHAT_COMPLETIONS_PATH = "/chat/completions"

# Matches model_pool.py's _MAX_SLOTS: at most this many distinct keys exist to
# try, so a bounded retry loop here can never spin more than once per
# configured key before giving up and raising.
_MAX_KEY_ATTEMPTS = 3


class ModelClientError(Exception):
    """Base class for every failure this module raises."""


class NoHealthyKeyError(ModelClientError):
    """No configured model API key is currently usable.

    Raised when the pool is unconfigured (zero ``MODEL_API_KEY_n`` set) or
    every configured key is currently quarantined. Callers must treat this
    the same way ``ModelKeyPool.get_healthy_key() is None`` is documented to
    be treated elsewhere: "no generative model available right now" — but
    this module raises rather than returning ``None``/fake data, per this
    wave's explicit instruction not to paper over total failure.
    """


class ModelAPIError(ModelClientError):
    """Every attempted key's HTTP call failed.

    ``status_code`` and ``response_body`` come from the remote API's own
    error response (never from request headers), so they are always safe to
    log — they cannot contain a key value. ``response_body`` is truncated to
    keep exception messages/log lines bounded.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


@dataclass(frozen=True)
class ChatCompletionResult:
    """Result of one successful chat-completion call."""

    text: str
    model: str
    latency_ms: float
    key_used: str  # e.g. "slot-2" — never the raw key value
    raw_usage: Optional[dict] = None


def _truncate(text: str, limit: int = 500) -> str:
    return text if len(text) <= limit else text[:limit] + "...(truncated)"


async def chat_completion(
    messages: list[dict],
    model: str,
    *,
    max_tokens: int = 300,
    temperature: float = 0.2,
    pool: Optional[ModelKeyPool] = None,
    timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
) -> ChatCompletionResult:
    """Make one OpenAI-compatible chat-completion request.

    Gets a healthy key from ``pool`` (a fresh ``ModelKeyPool()`` if none is
    given — matches every other module's "construct your own instance, no
    global singleton" convention), POSTs the standard OpenAI chat-completions
    body, and reports the real HTTP outcome back to the pool via
    ``report_success``/``report_failure`` so its quarantine/backoff state
    machine stays accurate.

    On a failed attempt with a key that still has other healthy siblings,
    this retries once per remaining healthy key (bounded by
    ``_MAX_KEY_ATTEMPTS``, matching the pool's max of 3 slots) before giving
    up. It never fabricates a response — total failure always raises.
    """

    active_pool = pool if pool is not None else ModelKeyPool()
    last_error: Optional[str] = None
    last_status: Optional[int] = None
    last_body: Optional[str] = None

    for _ in range(_MAX_KEY_ATTEMPTS):
        handle: Optional[KeyHandle] = active_pool.get_healthy_key()
        if handle is None:
            if last_error is not None:
                # Attempts were made and failed hard enough to quarantine
                # every key mid-loop — that's an API failure, not "never had
                # a key to try in the first place".
                raise ModelAPIError(
                    f"All model API keys exhausted after failures: {last_error}",
                    status_code=last_status,
                    response_body=last_body,
                )
            raise NoHealthyKeyError(
                "No healthy model API key available (unconfigured or all keys quarantined)."
            )

        url = f"{handle.base_url.rstrip('/')}{_CHAT_COMPLETIONS_PATH}"
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        headers = {
            "Authorization": f"Bearer {handle.api_key}",
            "Content-Type": "application/json",
        }

        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(url, headers=headers, json=payload)
            latency_ms = (time.monotonic() - start) * 1000
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            active_pool.report_failure(handle, status_code=status_code)
            last_status = status_code
            last_body = _truncate(exc.response.text or "")
            last_error = f"HTTP {status_code}: {last_body}"
            continue
        except httpx.HTTPError as exc:
            active_pool.report_failure(handle)
            last_error = f"{type(exc).__name__}: {exc}"
            continue

        try:
            body = response.json()
            choice = body["choices"][0]
            text = choice["message"]["content"]
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            active_pool.report_failure(handle)
            last_error = f"Malformed response body ({type(exc).__name__}): {_truncate(str(response.text))}"
            continue

        active_pool.report_success(handle)
        return ChatCompletionResult(
            text=text,
            model=body.get("model", model),
            latency_ms=latency_ms,
            key_used=f"slot-{handle.slot}",
            raw_usage=body.get("usage"),
        )

    raise ModelAPIError(
        f"chat_completion failed after {_MAX_KEY_ATTEMPTS} attempts: {last_error}",
        status_code=last_status,
        response_body=last_body,
    )
