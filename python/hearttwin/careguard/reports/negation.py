"""Deterministic negation detection (lightweight NegEx-style cue scan)."""

from __future__ import annotations

import re

_PRE_NEG = (
    "no evidence of", "no signs of", "no history of", "without", "denies", "negative for",
    "ruled out", "rule out", "r/o", "not consistent with", "absence of", "free of", "no ",
)
_RULED_OUT = ("ruled out", "rule out", "r/o", "excluded")


def is_negated(snippet: str) -> bool:
    low = snippet.lower()
    return any(cue in low for cue in _PRE_NEG)


def is_ruled_out(snippet: str) -> bool:
    low = snippet.lower()
    return any(cue in low for cue in _RULED_OUT)


def window(text: str, start: int, end: int, *, left: int = 40, right: int = 20) -> str:
    return text[max(0, start - left): min(len(text), end + right)]


_UNCERTAIN = ("possible", "probable", "likely", "cannot exclude", "suggestive of", "concern for", "?", "vs")


def is_uncertain(snippet: str) -> bool:
    low = snippet.lower()
    return any(cue in low for cue in _UNCERTAIN)
