from approvaltrace.analyzer.findings import classify_run


def test_hidden_model_content_is_failure() -> None:
    result = classify_run(
        hidden_model_content=True,
        material_mutation=False,
        reapproval_observed=False,
        changed_requests_before_reapproval=0,
    )
    assert result["result"] == "FAIL"
    assert result["severity"] == "high"


def test_absent_schema_is_partial_when_no_failure() -> None:
    result = classify_run(
        hidden_model_content=False,
        material_mutation=False,
        reapproval_observed=True,
        changed_requests_before_reapproval=0,
        schema_visibility="absent",
    )
    assert result["result"] == "PARTIAL"
