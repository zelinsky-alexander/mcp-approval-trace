from approvaltrace.analyzer.canonicalize import canonical_hash, canonical_json, unicode_views


def test_object_key_order_is_canonicalized() -> None:
    left = {"b": 2, "a": 1}
    right = {"a": 1, "b": 2}

    assert canonical_json(left) == canonical_json(right)
    assert canonical_hash(left) == canonical_hash(right)


def test_array_order_remains_significant() -> None:
    assert canonical_hash(["a", "b"]) != canonical_hash(["b", "a"])


def test_unicode_views_preserve_raw_and_expose_escape() -> None:
    views = unicode_views("safe\u200btext")

    assert views["raw"] == "safe\u200btext"
    assert "\\u200b" in views["escaped"]
