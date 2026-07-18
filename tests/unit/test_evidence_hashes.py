from pathlib import Path

from approvaltrace.evidence.manifest import verify_manifest, write_manifest


def test_detects_evidence_tampering(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence.json"
    evidence.write_text('{"value": 1}', encoding="utf-8")
    write_manifest(tmp_path)

    assert verify_manifest(tmp_path) == []

    evidence.write_text('{"value": 2}', encoding="utf-8")
    assert verify_manifest(tmp_path) == ["hash mismatch evidence.json"]
