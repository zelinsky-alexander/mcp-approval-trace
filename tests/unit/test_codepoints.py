from approvaltrace.analyzer.codepoints import (
    decode_tag_text,
    encode_tag_text,
    scan_codepoints,
)


def test_detects_and_decodes_tag_block() -> None:
    encoded = encode_tag_text("MARKER")
    findings = scan_codepoints("safe" + encoded)

    assert len(findings) == 7
    assert {item.category for item in findings} == {"unicode_tag_block"}
    assert decode_tag_text(encoded) == "MARKER"


def test_detects_zero_width_and_bidi_controls() -> None:
    value = "a\u200bb\u202ec\u2066d"
    categories = {item.category for item in scan_codepoints(value)}

    assert "zero_width_space" in categories
    assert "bidi_formatting" in categories
    assert "bidi_isolate" in categories


def test_does_not_flag_normal_multilingual_text() -> None:
    value = "שלום Привет café 😀"
    assert scan_codepoints(value) == []
