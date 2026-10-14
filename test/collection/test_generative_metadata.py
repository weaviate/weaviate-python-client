from typing import Type, Union

import pytest

from weaviate.collections.classes.internal import _QueryOptions
from weaviate.collections.queries.base_executor import _BaseExecutor
from weaviate.connect import ConnectionV4
from weaviate.proto.v1 import generative_pb2, search_get_pb2
from weaviate.util import _ServerVersion


@pytest.mark.parametrize(
    "provider,metadata_type",
    [
        ("digitalocean", generative_pb2.GenerativeDigitalOceanMetadata),
        ("meta", generative_pb2.GenerativeMetaMetadata),
    ],
    ids=["digitalocean", "meta"],
)
@pytest.mark.parametrize("grouped", [False, True], ids=["single", "grouped"])
def test_metadata_is_preserved_in_generative_results(
    connection: ConnectionV4,
    provider: str,
    metadata_type: Union[
        Type[generative_pb2.GenerativeDigitalOceanMetadata],
        Type[generative_pb2.GenerativeMetaMetadata],
    ],
    grouped: bool,
) -> None:
    connection._weaviate_version = _ServerVersion(1, 39, 0)
    executor = _BaseExecutor(connection, "Test", None, None, None, None, True)
    expected = metadata_type(
        usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
    )
    generative_metadata = generative_pb2.GenerativeMetadata()
    getattr(generative_metadata, provider).CopyFrom(expected)
    generative = generative_pb2.GenerativeResult(
        values=[
            generative_pb2.GenerativeReply(
                result="generated",
                metadata=generative_metadata,
            )
        ]
    )
    response = (
        search_get_pb2.SearchReply(generative_grouped_results=generative)
        if grouped
        else search_get_pb2.SearchReply(
            results=[search_get_pb2.SearchResult(generative=generative)]
        )
    )

    actual = executor._result_to_generative_query_return(
        response, _QueryOptions(False, False, False, False, False)
    )

    if grouped:
        assert actual.generative is not None
        metadata = actual.generative.metadata
    else:
        assert actual.objects[0].generative is not None
        metadata = actual.objects[0].generative.metadata
    assert metadata is not None
    assert isinstance(metadata, metadata_type)
    assert metadata == expected
    assert metadata.usage.prompt_tokens == 10
    assert metadata.usage.completion_tokens == 20
    assert metadata.usage.total_tokens == 30
