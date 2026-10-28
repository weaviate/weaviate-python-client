from typing import Awaitable, Optional

import pytest

from weaviate.collections.classes.internal import _QueryOptions
from weaviate.collections.queries.base_executor import _BaseExecutor
from weaviate.collections.query import _QueryCollectionAsync
from weaviate.connect import ConnectionV4
from weaviate.exceptions import WeaviateInvalidInputError
from weaviate.proto.v1 import generative_pb2, search_get_pb2
from weaviate.util import _ServerVersion

# TODO: re-enable tests once string syntax is re-enabled in the API

# from typing import List, Optional, Union

# import pytest

# from weaviate.collections.classes.grpc import (
#     PROPERTIES,
#     FromReference,
#     FromReferenceMultiTarget,
# )
# from weaviate.collections.queries.base import _PropertiesParser

# @pytest.mark.parametrize(
#     "properties,output",
#     [
#         (["name"], ["name"]),
#         ([FromReference(link_on="name")], [FromReference(link_on="name")]),
#         (["name", FromReference(link_on="name")], ["name", FromReference(link_on="name")]),
#         (
#             [FromReferenceMultiTarget(link_on="name", target_collection="Test"), "name"],
#             ["name", FromReferenceMultiTarget(link_on="name", target_collection="Test")],
#         ),
#         (
#             ["__article__properties__name"],
#             [FromReference(link_on="article", return_properties=["name"])],
#         ),
#         (
#             ["__article__properties__name", "name", "__article__properties__age"],
#             ["name", FromReference(link_on="article", return_properties=["name", "age"])],
#         ),
#         (["__article"], [FromReference(link_on="article")]),
#         (
#             ["__article", "__article__properties__name"],
#             [FromReference(link_on="article", return_properties=["name"])],
#         ),
#         (
#             ["__article__properties__name", "__article"],
#             [FromReference(link_on="article", return_properties=["name"])],
#         ),
#         (None, None),
#         ([None, "name"], ["name"]),
#         (["__article", "name"], ["name", FromReference(link_on="article")]),
#         ("__article", [FromReference(link_on="article")]),
#         ("__article__", [FromReference(link_on="article")]),
#     ],
# )
# def test_properties_parser_success(properties: Optional[PROPERTIES], output: Optional[PROPERTIES]):
#     assert output == _PropertiesParser().parse(properties)


# ERROR_MESSAGE = (
#     lambda s: f"return reference property {s} must be in the format __{{prop_name}} or __{{prop_name}}__{{properties|metadata}}_{{nested_prop_name}} when using string syntax"
# )


# @pytest.mark.skip(reason="string syntax has been temporarily removed from the API")
# @pytest.mark.parametrize(
#     "wrong",
#     [
#         ["__article__propertie__uuid"],
#         ["__article__propertiess__uuid"],
#         ["__article__metadat__uuid"],
#         ["__article__metadataa__uuid"],
#         "__article__propertie__uuid",
#         "__article__propertiess__uuid",
#         "__article__metadat__uuid",
#         "__article__metadataa__uuid",
#     ],
# )
# def test_properties_parser_error(wrong: Union[str, List[str]]):
#     with pytest.raises(ValueError) as e:
#         out = _PropertiesParser().parse(wrong)
#         print(out)
#     assert e.value.args[0] == ERROR_MESSAGE(wrong[0] if len(wrong) == 1 else wrong)


async def _test_query(query: Awaitable) -> None:
    with pytest.raises(WeaviateInvalidInputError):
        await query()


@pytest.mark.asyncio
async def test_bad_query_inputs(connection: ConnectionV4) -> None:
    query = _QueryCollectionAsync(connection, "dummy", None, None, None, None, True)
    # fetch_objects
    await _test_query(lambda: query.fetch_objects(limit="thing"))
    await _test_query(lambda: query.fetch_objects(offset="wrong"))
    await _test_query(lambda: query.fetch_objects(after=42))
    await _test_query(lambda: query.fetch_objects(filters="wrong"))
    await _test_query(lambda: query.fetch_objects(sort="wrong"))
    await _test_query(lambda: query.fetch_objects(include_vector=42))
    await _test_query(lambda: query.fetch_objects(return_metadata=42))
    await _test_query(lambda: query.fetch_objects(return_properties=42))
    await _test_query(lambda: query.fetch_objects(return_references="wrong"))

    # bm25
    await _test_query(lambda: query.bm25(42))
    await _test_query(lambda: query.bm25("hi", query_properties="wrong"))
    await _test_query(lambda: query.bm25("hi", auto_limit="wrong"))
    await _test_query(lambda: query.bm25("hi", rerank="wrong"))

    # hybrid
    await _test_query(lambda: query.hybrid(42))
    await _test_query(lambda: query.hybrid("hi", query_properties="wrong"))
    await _test_query(lambda: query.hybrid("hi", alpha="wrong"))
    await _test_query(lambda: query.hybrid("hi", vector="wrong"))
    await _test_query(lambda: query.hybrid("hi", fusion_type="wrong"))

    # near text
    await _test_query(lambda: query.near_text(42))
    await _test_query(lambda: query.near_text("hi", certainty="wrong"))
    await _test_query(lambda: query.near_text("hi", distance="wrong"))
    await _test_query(lambda: query.near_text("hi", move_to="wrong"))
    await _test_query(lambda: query.near_text("hi", move_away="wrong"))

    # near object
    await _test_query(lambda: query.near_object(42))

    # near vector
    await _test_query(lambda: query.near_vector(42))

    # near image
    await _test_query(lambda: query.near_image(42))


@pytest.mark.parametrize(
    "version,uses_125_api,uses_127_api",
    [
        ("1.24.0", False, False),
        ("1.26.0", True, False),
        ("1.27.0", True, True),
        ("1.32.5", True, True),
    ],
)
def test_query_uses_version_learned_after_construction(
    connection: ConnectionV4, version: str, uses_125_api: bool, uses_127_api: bool
) -> None:
    # The async client only learns the server version inside `connect()`, so a collection object
    # made before `await client.connect()` is built against version 0.0.0, see issue #1831.
    query = _QueryCollectionAsync(connection, "dummy", None, None, None, None, True)
    assert connection._weaviate_version == _ServerVersion(0, 0, 0)

    connection._weaviate_version = _ServerVersion.from_string(version)

    request = query._query.get()
    assert request.uses_125_api is uses_125_api
    assert request.uses_127_api is uses_127_api


def test_query_rereads_version_on_every_access(connection: ConnectionV4) -> None:
    # The version is resolved per call rather than cached on first use, so a connection that
    # starts talking to a different server is picked up as well.
    query = _QueryCollectionAsync(connection, "dummy", None, None, None, None, True)

    connection._weaviate_version = _ServerVersion(1, 26, 0)
    assert query._query.get().uses_127_api is False

    connection._weaviate_version = _ServerVersion(1, 32, 5)
    assert query._query.get().uses_127_api is True


@pytest.mark.parametrize("version,generated", [("1.26.0", None), ("1.32.5", "generated")])
def test_query_generative_uses_version_learned_after_construction(
    connection: ConnectionV4, version: str, generated: Optional[str]
) -> None:
    executor = _BaseExecutor(connection, "dummy", None, None, None, None, True)

    connection._weaviate_version = _ServerVersion.from_string(version)

    # The generated text is only present in the generative field, which is the field that servers
    # from 1.27 onwards fill, so a stale version reads the empty deprecated metadata field instead.
    response = search_get_pb2.SearchReply(
        results=[
            search_get_pb2.SearchResult(
                generative=generative_pb2.GenerativeResult(
                    values=[generative_pb2.GenerativeReply(result="generated")]
                )
            )
        ]
    )
    result = executor._result_to_generative_query_return(
        response,
        _QueryOptions(
            include_metadata=False,
            include_properties=False,
            include_references=False,
            include_vector=False,
            is_group_by=False,
        ),
    )
    assert result.objects[0].generated == generated
