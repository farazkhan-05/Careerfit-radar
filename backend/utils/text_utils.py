from __future__ import annotations

import re
import unicodedata

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return _WHITESPACE_RE.sub(" ", normalized).strip()


def normalize_for_match(value: str) -> str:
    return normalize_text(value).casefold()
