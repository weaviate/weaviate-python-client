import pytest
import weaviate


def test_none_api_key_header() -> None:
    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError) as e:
        weaviate.use_async_with_local(headers={"X-OpenAI-Api-Key": None})
    assert "X-OpenAI-Api-Key" in e.value.message


@pytest.mark.asyncio
async def test_sync_in_async_warning() -> None:
    with pytest.warns(UserWarning) as record:
        try:
            weaviate.connect_to_local(skip_init_checks=True)
        except weaviate.exceptions.WeaviateStartUpError:
            pass
    assert len(record) == 1
    assert "You're using the sync client in an async context" in record[0].message.args[0]
