from __future__ import annotations

import unicodedata
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class CodePointFinding:
    index: int
    character: str
    codepoint: str
    name: str
    category: str


DANGEROUS_RANGES: tuple[tuple[int, int, str], ...] = (
    (0xE0000, 0xE007F, "unicode_tag_block"),
    (0x202A, 0x202E, "bidi_formatting"),
    (0x2066, 0x2069, "bidi_isolate"),
)

DANGEROUS_POINTS: dict[int, str] = {
    0x200B: "zero_width_space",
    0x200C: "zero_width_non_joiner",
    0x200D: "zero_width_joiner",
    0x2060: "word_joiner",
    0xFEFF: "zero_width_no_break_space_or_bom",
}


def classify_codepoint(value: int) -> str | None:
    if value in DANGEROUS_POINTS:
        return DANGEROUS_POINTS[value]
    for start, end, category in DANGEROUS_RANGES:
        if start <= value <= end:
            return category
    return None


def scan_codepoints(text: str) -> list[CodePointFinding]:
    findings: list[CodePointFinding] = []
    for index, character in enumerate(text):
        code = ord(character)
        category = classify_codepoint(code)
        if category:
            findings.append(
                CodePointFinding(
                    index=index,
                    character=character,
                    codepoint=f"U+{code:04X}",
                    name=unicodedata.name(character, "UNNAMED"),
                    category=category,
                )
            )
    return findings


def findings_as_dicts(text: str) -> list[dict[str, object]]:
    return [asdict(item) for item in scan_codepoints(text)]


def encode_tag_text(text: str, terminate: bool = True) -> str:
    """Encode printable ASCII as Unicode TAG characters for controlled fixtures."""
    encoded: list[str] = []
    for character in text:
        code = ord(character)
        if not 0x20 <= code <= 0x7E:
            raise ValueError("TAG fixture encoder only accepts printable ASCII")
        encoded.append(chr(0xE0000 + code))
    if terminate:
        encoded.append(chr(0xE007F))
    return "".join(encoded)


def decode_tag_text(text: str) -> str:
    decoded: list[str] = []
    for character in text:
        code = ord(character)
        if code == 0xE007F:
            continue
        if 0xE0020 <= code <= 0xE007E:
            decoded.append(chr(code - 0xE0000))
    return "".join(decoded)
