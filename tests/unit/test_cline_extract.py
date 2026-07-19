from approvaltrace.automation.cline_extract import extract_model_tool


def test_extracts_cline_prompt_embedded_tool() -> None:
    body = {
        "messages": [
            {
                "role": "system",
                "content": """# Connected MCP Servers

## approvaltrace (`python -m mutation_server.server`)

### Available Tools
- search_test_documents: Search test documents.
    Input Schema:
    {
      "type": "object",
      "properties": {
        "query": {"type": "string", "description": "Search phrase."}
      },
      "required": ["query"],
      "additionalProperties": false
    }

====
""",
            }
        ]
    }

    tool, method = extract_model_tool(
        body, server_name="approvaltrace", tool_name="search_test_documents"
    )

    assert method == "cline_system_prompt"
    assert tool is not None
    assert tool["name"] == "search_test_documents"
    assert tool["inputSchema"]["properties"]["query"]["type"] == "string"


def test_prefers_native_openai_tools() -> None:
    body = {
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "search_test_documents",
                    "description": "Search.",
                    "parameters": {"type": "object"},
                },
            }
        ]
    }

    tool, method = extract_model_tool(
        body, server_name="approvaltrace", tool_name="search_test_documents"
    )

    assert method == "openai_tools"
    assert tool is not None
    assert tool["description"] == "Search."
