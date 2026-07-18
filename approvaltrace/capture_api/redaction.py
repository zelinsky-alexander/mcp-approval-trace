from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

_SECRET_KEYS = {
    "authorization",
    "api_key",
    "apikey",
    "api-key",
    "token",
    "access_token",
    "refresh_token",
    "cookie",
    "set-cookie",
}

_WINDOWS_HOME = re.compile(r"(?i)\b[A-Z]:\\Users\\[^\\\s\"']+")
_UNIX_HOME = re.compile(r"(?<![\w-])/home/[^/\s\"']+")
_BEARER = re.compile(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]+")
_SK_TOKEN = re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b")


def _redact_string(value: str) -> str:
    value = _BEARER.sub("Bearer [REDACTED]", value)
    value = _SK_TOKEN.sub("[REDACTED_API_KEY]", value)
    value = _WINDOWS_HOME.sub(r"C:\\Users\\[REDACTED_USER]", value)
    return _UNIX_HOME.sub("/home/[REDACTED_USER]", value)


def redact(value: Any) -> Any:
    """Return a deep, publication-safe copy of JSON-compatible data."""
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if key.lower() in _SECRET_KEYS:
                result[key] = "[REDACTED]"
            else:
                result[key] = redact(item)
        return result
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return _redact_string(value)
    return deepcopy(value)
