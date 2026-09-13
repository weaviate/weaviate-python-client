import pytest

def format_bearer_token(token: str) -> str:
    cleaned = token.strip()
    if cleaned.lower().startswith("bearer "):
        return f"Bearer {cleaned[7:].strip()}"
    return f"Bearer {cleaned}"

def test_bearer_token_formatting():
    assert format_bearer_token("abc123key") == "Bearer abc123key"
    assert format_bearer_token("Bearer abc123key") == "Bearer abc123key"
    assert format_bearer_token("  bearer my-secret-token  ") == "Bearer my-secret-token"
