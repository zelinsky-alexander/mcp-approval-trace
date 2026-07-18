from approvaltrace.analyzer.compare import compare_server_to_model


def test_reports_server_to_model_field_differences() -> None:
    server = {
        "name": "search",
        "description": "Initial",
        "inputSchema": {"type": "object"},
    }
    model = {
        "name": "search",
        "description": "Changed",
        "inputSchema": {"type": "object"},
    }

    deltas = {item.path: item for item in compare_server_to_model(server, model)}

    assert deltas["name"].status == "match"
    assert deltas["description"].status == "different"
