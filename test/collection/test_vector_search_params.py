"""Unit tests: ``vector_search_params`` is wired into ``SearchRequest.vector_search_params``.

The option is a per-request override of the collection's HNSW ``ef``. These tests pin the
request-building contract only: the field is set exactly when the caller passes it, an omitted
option leaves the request byte-identical to before the option existed, and the client validates
only what the wire format cannot express (types, sign); caps and the bm25 rule stay server-side.
"""

from typing import Callable

import pytest
from pydantic import ValidationError

from weaviate.classes.query import HybridVector, VectorSearchParams
from weaviate.collections.grpc.query import _QueryGRPC
from weaviate.exceptions import WeaviateInvalidInputError, WeaviateUnsupportedFeatureError
from weaviate.proto.v1 import search_get_pb2
from weaviate.util import _ServerVersion

_UUID = "00000000-0000-0000-0000-000000000001"
_DEFAULT_VERSION = _ServerVersion(1, 41, 0)


def _builder(version: _ServerVersion = _DEFAULT_VERSION) -> _QueryGRPC:
    return _QueryGRPC(
        weaviate_version=version,
        name="Dummy",
        tenant=None,
        consistency_level=None,
        validate_arguments=True,
        uses_125_api=True,
        uses_127_api=True,
    )


# Every vector-search entry point, each with its minimal required arguments.
_VECTOR_SEARCHES: dict[str, Callable[[_QueryGRPC, dict], search_get_pb2.SearchRequest]] = {
    "near_vector": lambda b, kw: b.near_vector(near_vector=[1.0, 0.0, 0.0], **kw),
    "near_object": lambda b, kw: b.near_object(near_object=_UUID, **kw),
    "near_text": lambda b, kw: b.near_text(near_text="cats", **kw),
    "near_media": lambda b, kw: b.near_media(media="YWJj", type_="image", **kw),
    "hybrid_bm25_and_vector": lambda b, kw: b.hybrid(
        query="cats", vector=HybridVector.near_vector(vector=[1.0, 0.0, 0.0]), **kw
    ),
    "hybrid_query_only": lambda b, kw: b.hybrid(query="cats", **kw),
}


@pytest.mark.parametrize("build", _VECTOR_SEARCHES.values(), ids=_VECTOR_SEARCHES.keys())
def test_ef_is_sent_when_given(
    build: Callable[[_QueryGRPC, dict], search_get_pb2.SearchRequest],
) -> None:
    req = build(_builder(), {"vector_search_params": VectorSearchParams(ef=64)})
    assert req.HasField("vector_search_params")
    assert req.vector_search_params.HasField("ef")
    assert req.vector_search_params.ef == 64


@pytest.mark.parametrize("build", _VECTOR_SEARCHES.values(), ids=_VECTOR_SEARCHES.keys())
def test_field_absent_when_not_given(
    build: Callable[[_QueryGRPC, dict], search_get_pb2.SearchRequest],
) -> None:
    req = build(_builder(), {})
    assert not req.HasField("vector_search_params")


@pytest.mark.parametrize("build", _VECTOR_SEARCHES.values(), ids=_VECTOR_SEARCHES.keys())
def test_none_is_byte_identical_to_omitting(
    build: Callable[[_QueryGRPC, dict], search_get_pb2.SearchRequest],
) -> None:
    omitted = build(_builder(), {})
    explicit_none = build(_builder(), {"vector_search_params": None})
    assert explicit_none.SerializeToString(deterministic=True) == omitted.SerializeToString(
        deterministic=True
    )


def test_params_without_ef_send_an_empty_message() -> None:
    # The server reads an unset ef as "use the collection default".
    req = _builder().near_vector(
        near_vector=[1.0, 0.0, 0.0], vector_search_params=VectorSearchParams()
    )
    assert req.HasField("vector_search_params")
    assert not req.vector_search_params.HasField("ef")


def test_explicit_zero_is_sent_as_zero() -> None:
    # 0 is a legal wire value meaning "collection default"; the client does not drop it.
    req = _builder().near_vector(
        near_vector=[1.0, 0.0, 0.0], vector_search_params=VectorSearchParams(ef=0)
    )
    assert req.vector_search_params.HasField("ef")
    assert req.vector_search_params.ef == 0


def test_ef_below_limit_is_sent_unchanged() -> None:
    # Flooring ef at k is the server's job (max(ef, k)); the client must not second-guess it.
    req = _builder().near_vector(
        near_vector=[1.0, 0.0, 0.0], limit=10, vector_search_params=VectorSearchParams(ef=2)
    )
    assert req.limit == 10
    assert req.vector_search_params.ef == 2


def test_other_fields_untouched_by_ef() -> None:
    with_ef = _builder().near_vector(
        near_vector=[1.0, 0.0, 0.0], limit=5, vector_search_params=VectorSearchParams(ef=64)
    )
    without = _builder().near_vector(near_vector=[1.0, 0.0, 0.0], limit=5)
    with_ef.ClearField("vector_search_params")
    assert with_ef.SerializeToString(deterministic=True) == without.SerializeToString(
        deterministic=True
    )


@pytest.mark.parametrize("bad", [{"ef": 64}, 64, "64", (64,)])
def test_wrong_type_rejected_client_side(bad: object) -> None:
    with pytest.raises(WeaviateInvalidInputError):
        _builder().near_vector(near_vector=[1.0, 0.0, 0.0], vector_search_params=bad)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "bad_ef",
    [-1, 2**32, True, "64", 1.5, 64.0],
    ids=["negative", "above-uint32", "bool", "str", "float", "integral-float"],
)
def test_ef_must_be_a_uint32(bad_ef: object) -> None:
    # uint32 on the wire: negative or >= 2**32 values are unrepresentable and would otherwise fail
    # inside protobuf with a bare ValueError; bool/str/float would be silently coerced by lax
    # pydantic, so the field is strict.
    with pytest.raises(ValidationError):
        VectorSearchParams(ef=bad_ef)  # type: ignore[arg-type]


def test_uint32_max_is_sent_for_the_server_to_reject() -> None:
    # The last representable value is legal on the wire; the HNSW_MAX_SEARCH_EF cap is the server's.
    req = _builder().near_vector(
        near_vector=[1.0, 0.0, 0.0], vector_search_params=VectorSearchParams(ef=2**32 - 1)
    )
    assert req.vector_search_params.ef == 2**32 - 1


def test_unknown_params_rejected() -> None:
    # Keeps a typo (or a not-yet-supported knob such as search_probe) from being silently dropped.
    with pytest.raises(ValidationError):
        VectorSearchParams(search_probe=3)  # type: ignore[call-arg]


def test_not_offered_on_keyword_only_searches() -> None:
    # The server rejects vector_search_params on bm25-only requests and it is meaningless for
    # fetch_objects, so neither builder accepts the keyword.
    with pytest.raises(TypeError):
        _builder().bm25(query="cats", vector_search_params=VectorSearchParams(ef=64))  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        _builder().get(vector_search_params=VectorSearchParams(ef=64))  # type: ignore[call-arg]


@pytest.mark.parametrize("build", _VECTOR_SEARCHES.values(), ids=_VECTOR_SEARCHES.keys())
def test_rejected_on_servers_without_the_feature(
    build: Callable[[_QueryGRPC, dict], search_get_pb2.SearchRequest],
) -> None:
    # A pre-1.41 server would drop the unknown field and silently search with the collection ef.
    with pytest.raises(WeaviateUnsupportedFeatureError, match="1.41.0"):
        build(
            _builder(_ServerVersion(1, 40, 2)), {"vector_search_params": VectorSearchParams(ef=64)}
        )


def test_old_server_fine_without_the_option() -> None:
    req = _builder(_ServerVersion(1, 40, 2)).near_vector(near_vector=[1.0, 0.0, 0.0])
    assert not req.HasField("vector_search_params")


def test_release_candidate_of_minimum_version_accepted() -> None:
    req = _builder(_ServerVersion.from_string("1.41.0-rc.0")).near_vector(
        near_vector=[1.0, 0.0, 0.0], vector_search_params=VectorSearchParams(ef=64)
    )
    assert req.vector_search_params.ef == 64
