from approvaltrace.analyzer.schema_paths import flatten_tool


def test_extracts_nested_security_relevant_paths() -> None:
    tool = {
        "name": "search",
        "description": "Search",
        "inputSchema": {
            "type": "object",
            "properties": {
                "export_target": {
                    "type": "string",
                    "description": "Marker NESTED_FIELD_PRESENT",
                }
            },
            "required": ["export_target"],
        },
        "unrelated": "ignored",
    }

    paths = flatten_tool(tool)

    assert paths["inputSchema.properties.export_target.description"] == (
        "Marker NESTED_FIELD_PRESENT"
    )
    assert paths["inputSchema.required[0]"] == "export_target"
    assert "unrelated" not in paths
