from approvaltrace.capture_api.redaction import redact


def test_redacts_secrets_and_home_paths() -> None:
    value = {
        "authorization": "Bearer super-secret-token",
        "api_key": "sk-testsecret123",
        "message": "C:\\Users\\Alex\\project /home/alex/project Bearer another-token",
    }

    result = redact(value)

    assert result["authorization"] == "[REDACTED]"
    assert result["api_key"] == "[REDACTED]"
    assert "Alex" not in result["message"]
    assert "/home/alex" not in result["message"]
    assert "another-token" not in result["message"]
