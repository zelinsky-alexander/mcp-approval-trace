from __future__ import annotations

import hashlib
import json
import unicodedata
from typing import Any


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_hash(value: Any) -> str:
    return sha256_text(canonical_json(value))


def unicode_views(text: str) -> dict[str, str]:
    return {
        "raw": text,
        "nfc": unicodedata.normalize("NFC", text),
        "nfkc": unicodedata.normalize("NFKC", text),
        "escaped": text.encode("unicode_escape").decode("ascii"),
    }
