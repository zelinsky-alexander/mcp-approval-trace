from __future__ import annotations

from typing import Any


def classify_run(
    *,
    hidden_model_content: bool,
    material_mutation: bool,
    reapproval_observed: bool | None,
    changed_requests_before_reapproval: int,
    schema_visibility: str | None = None,
) -> dict[str, Any]:
    reasons: list[str] = []
    severity = "info"
    result = "PASS"

    if hidden_model_content:
        result = "FAIL"
        severity = "high"
        reasons.append("hidden_model_bound_content_not_visibly_represented")
    if material_mutation and not reapproval_observed and changed_requests_before_reapproval > 0:
        result = "FAIL"
        severity = "high"
        reasons.append("changed_metadata_used_before_reapproval")
    if result == "PASS" and schema_visibility in {"absent", "partial", "truncated"}:
        result = "PARTIAL"
        severity = "medium"
        reasons.append("model_bound_schema_not_fully_visible")
    if reapproval_observed is None:
        result = "INCONCLUSIVE" if result == "PASS" else result
        reasons.append("reapproval_observation_unavailable")

    return {"result": result, "severity": severity, "reasons": reasons}
