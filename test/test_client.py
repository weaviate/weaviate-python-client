import pytest
import weaviate


def test_none_api_key_header() -> None:
    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError) as e:
        weaviate.use_async_with_local(headers={"X-OpenAI-Api-Key": None})
    assert "X-OpenAI-Api-Key" in e.value.message
