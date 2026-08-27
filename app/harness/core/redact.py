"""Strip credential-shaped substrings before text is logged, stored, or shown to a human."""

from __future__ import annotations

import re

_PATTERNS = [
    re.compile(p)
    for p in (
        r"xox[abpe]-[A-Za-z0-9-]+",          # Slack tokens
        r"lin_api_[A-Za-z0-9]+",             # Linear
        r"ntn_[A-Za-z0-9]+",                 # Notion
        r"whsec_[A-Za-z0-9+/=]+",            # webhook secrets
        r"AIza[0-9A-Za-z_-]{20,}",           # Google API keys
        r"Bearer\s+[A-Za-z0-9._-]+",         # bearer tokens
    )
]


def redact(text: str) -> str:
    out = text
    for pattern in _PATTERNS:
        out = pattern.sub("[redacted]", out)
    return out
