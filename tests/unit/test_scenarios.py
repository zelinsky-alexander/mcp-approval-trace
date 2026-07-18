from pathlib import Path

from approvaltrace.analyzer.codepoints import decode_tag_text, scan_codepoints
from mutation_server.scenario import load_scenario, tool_for_phase


def test_all_scenarios_are_loadable(monkeypatch) -> None:
    root = Path(__file__).parents[2] / "mutation_server" / "scenarios"
    monkeypatch.setenv("APPROVALTRACE_SCENARIO_DIR", str(root))

    for scenario_id in ["AT-001", "AT-002", "AT-003", "AT-004", "AT-005", "AT-006"]:
        scenario = load_scenario(scenario_id)
        assert scenario["id"] == scenario_id
        assert tool_for_phase(scenario, "initial")["name"] == "search_test_documents"


def test_tag_scenario_contains_controlled_marker(monkeypatch) -> None:
    root = Path(__file__).parents[2] / "mutation_server" / "scenarios"
    monkeypatch.setenv("APPROVALTRACE_SCENARIO_DIR", str(root))
    scenario = load_scenario("AT-002")
    description = tool_for_phase(scenario, "initial")["description"]

    assert scan_codepoints(description)
    assert decode_tag_text(description) == "APPROVALTRACE_TAG_MARKER"


def test_schema_expansion_changes_required_and_properties(monkeypatch) -> None:
    root = Path(__file__).parents[2] / "mutation_server" / "scenarios"
    monkeypatch.setenv("APPROVALTRACE_SCENARIO_DIR", str(root))
    scenario = load_scenario("AT-004")
    initial = tool_for_phase(scenario, "initial")
    mutated = tool_for_phase(scenario, "mutated")

    assert "export_target" not in initial["inputSchema"]["properties"]
    assert "export_target" in mutated["inputSchema"]["properties"]
    assert mutated["inputSchema"]["required"] == ["query", "export_target"]
