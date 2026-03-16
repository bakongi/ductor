"""Output sanitization: redact secrets from CLI responses before delivery."""

from __future__ import annotations

import re

_SECRET_PATTERNS: list[re.Pattern[str]] = [
    # ENV_VAR=value (API_KEY, TOKEN, SECRET, PASSWORD, CREDENTIAL, AUTH)
    re.compile(
        r"([A-Za-z0-9_]*(?:API[_-]?KEY|APIKEY|TOKEN|SECRET|PASSWORD"
        r"|PASS|CREDENTIAL|AUTH)[A-Za-z0-9_]*)=([^\s\n]+)",
        re.IGNORECASE,
    ),
    # OpenAI API keys
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    # Anthropic API keys
    re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
    # GitHub tokens
    re.compile(r"ghp_[A-Za-z0-9]{36,}"),
    # Telegram bot tokens
    re.compile(r"\d{8,12}:[A-Za-z0-9_-]{35}"),
    # Bearer tokens
    re.compile(r"Bearer\s+[A-Za-z0-9._-]{20,}"),
]


def sanitize_output(text: str) -> str:
    """Replace detected secrets with ``[REDACTED]``.

    Returns the sanitized text. Short or empty inputs are returned as-is.
    """
    if len(text) < 10:
        return text
    result = text
    for pattern in _SECRET_PATTERNS:
        result = pattern.sub("[REDACTED]", result)
    return result
