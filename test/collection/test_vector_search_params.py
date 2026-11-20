"""Unit tests: ``vector_search_params`` is wired into the two ``SearchRequest`` wire fields.

A single ``VectorSearchParams`` lands in ``vector_search_params`` (request-wide); a mapping keyed by
target vector name becomes one ``vector_search_params_for_targets`` entry each. These tests pin the
request-building contract only: the fields are set exactly when the caller passes them, an omitted
option leaves the request byte-identical to before the option existed, and the client validates
only what the wire format cannot express (types, sign, unknown strategy names); caps, target-name
checks and the bm25 rule stay server-side so their error text comes from one place.
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


def test_params_without_fields_send_an_empty_message() -> None:
    # The server reads every unset field as "use the collection default".
    req = _builder().near_vector(
        near_vector=[1.0, 0.0, 0.0], vector_search_params=VectorSearchParams()
    )
    assert req.HasField("vector_search_params")
    assert not req.vector_search_params.HasField("ef")
    assert not req.vector_search_params.HasField("search_probe")
    assert not req.vector_search_params.HasField("filter_strategy")
    assert len(req.vector_search_params_for_targets) == 0


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
    # Keeps a typo (or a knob that only exists in the collection config) from being silently dropped.
    with pytest.raises(ValidationError):
        VectorSearchParams(efConstruction=3)  # type: ignore[call-arg]


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


def test_mapping_rejected_on_servers_without_the_feature() -> None:
    with pytest.raises(WeaviateUnsupportedFeatureError, match="1.41.0"):
        _builder(_ServerVersion(1, 40, 2)).near_vector(
            near_vector=[1.0, 0.0, 0.0],
            vector_search_params={"title": VectorSearchParams(ef=64)},
        )


def test_old_server_fine_without_the_option() -> None:
    req = _builder(_ServerVersion(1, 40, 2)).near_vector(near_vector=[1.0, 0.0, 0.0])
    assert not req.HasField("vector_search_params")


def test_release_candidate_of_minimum_version_accepted() -> None:
    req = _builder(_ServerVersion.from_string("1.41.0-rc.0")).near_vector(
        near_vector=[1.0, 0.0, 0.0], vector_search_params=VectorSearchParams(ef=64)
    )
    assert req.vector_search_params.ef == 64


# --- all knobs on one message ---------------------------------------------------------------


def test_all_fields_are_sent_together() -> None:
    req = _builder().near_vector(
        near_vector=[1.0, 0.0, 0.0],
        vector_search_params=VectorSearchParams(ef=64, search_probe=8, filter_strategy="acorn"),
    )
    params = req.vector_search_params
    assert params.ef == 64
    assert params.search_probe == 8
    assert params.filter_strategy == search_get_pb2.FILTER_STRATEGY_ACORN


def test_search_probe_alone_leaves_hnsw_fields_unset() -> None:
    req = _builder().near_vector(
        near_vector=[1.0, 0.0, 0.0], vector_search_params=VectorSearchParams(search_probe=3)
    )
    params = req.vector_search_params
    assert params.HasField("search_probe") and params.search_probe == 3
    assert not params.HasField("ef")
    assert not params.HasField("filter_strategy")


@pytest.mark.parametrize(
    "name,expected",
    [
        ("sweeping", search_get_pb2.FILTER_STRATEGY_SWEEPING),
        ("acorn", search_get_pb2.FILTER_STRATEGY_ACORN),
        ("pathseer", search_get_pb2.FILTER_STRATEGY_PATHSEER),
    ],
)
def test_filter_strategy_maps_to_enum(name: str, expected: int) -> None:
    req = _builder().near_vector(
        near_vector=[1.0, 0.0, 0.0],
        vector_search_params=VectorSearchParams(filter_strategy=name),  # type: ignore[arg-type]
    )
    assert req.vector_search_params.HasField("filter_strategy")
    assert req.vector_search_params.filter_strategy == expected
    # UNSPECIFIED is never sent explicitly: None leaves the field unset instead.
    assert expected != search_get_pb2.FILTER_STRATEGY_UNSPECIFIED


@pytest.mark.parametrize("bad", ["ACORN", "Acorn", "unspecified", "", 1, True])
def test_unknown_filter_strategy_rejected_client_side(bad: object) -> None:
    # Cheap to check here; the server would also answer InvalidArgument for an unknown enum value.
    with pytest.raises(ValidationError):
        VectorSearchParams(filter_strategy=bad)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "bad",
    [-1, 2**32, True, "8", 1.5],
    ids=["negative", "above-uint32", "bool", "str", "float"],
)
def test_search_probe_must_be_a_uint32(bad: object) -> None:
    with pytest.raises(ValidationError):
        VectorSearchParams(search_probe=bad)  # type: ignore[arg-type]


# --- constructors --------------------------------------------------------------------------


def test_hnsw_constructor_sets_only_hnsw_knobs() -> None:
    params = VectorSearchParams.hnsw(ef=32, filter_strategy="pathseer")
    assert params == VectorSearchParams(ef=32, filter_strategy="pathseer")
    assert params.search_probe is None
    assert VectorSearchParams.hnsw() == VectorSearchParams()


def test_hfresh_constructor_sets_only_search_probe() -> None:
    params = VectorSearchParams.hfresh(search_probe=12)
    assert params == VectorSearchParams(search_probe=12)
    assert params.ef is None and params.filter_strategy is None
    assert VectorSearchParams.hfresh() == VectorSearchParams()


def test_dynamic_constructor_forwards_hnsw_knobs() -> None:
    assert VectorSearchParams.dynamic() == VectorSearchParams()
    assert VectorSearchParams.dynamic(hnsw=VectorSearchParams.hnsw(ef=48)) == VectorSearchParams(
        ef=48
    )
    # A dynamic index has no HFresh stage: a stray search_probe is not forwarded.
    forwarded = VectorSearchParams.dynamic(
        hnsw=VectorSearchParams(ef=48, search_probe=5, filter_strategy="acorn")
    )
    assert forwarded == VectorSearchParams(ef=48, filter_strategy="acorn")


@pytest.mark.parametrize("bad", [-1, "32", 1.5])
def test_constructors_validate_like_the_class(bad: object) -> None:
    with pytest.raises(ValidationError):
        VectorSearchParams.hnsw(ef=bad)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        VectorSearchParams.hfresh(search_probe=bad)  # type: ignore[arg-type]


# --- per-target mapping ----------------------------------------------------------------------


@pytest.mark.parametrize("build", _VECTOR_SEARCHES.values(), ids=_VECTOR_SEARCHES.keys())
def test_mapping_becomes_per_target_entries_and_no_request_wide_field(
    build: Callable[[_QueryGRPC, dict], search_get_pb2.SearchRequest],
) -> None:
    req = build(
        _builder(),
        {
            "vector_search_params": {
                "title": VectorSearchParams.hnsw(ef=16),
                "body": VectorSearchParams.hfresh(search_probe=4),
            }
        },
    )
    assert not req.HasField("vector_search_params")
    by_target = {e.target: e.params for e in req.vector_search_params_for_targets}
    assert set(by_target) == {"title", "body"}
    assert by_target["title"].ef == 16
    assert not by_target["title"].HasField("search_probe")
    assert by_target["body"].search_probe == 4
    assert not by_target["body"].HasField("ef")


def test_mapping_preserves_insertion_order() -> None:
    req = _builder().near_vector(
        near_vector=[1.0, 0.0, 0.0],
        vector_search_params={
            "c": VectorSearchParams(ef=3),
            "a": VectorSearchParams(ef=1),
            "b": VectorSearchParams(ef=2),
        },
    )
    assert [e.target for e in req.vector_search_params_for_targets] == ["c", "a", "b"]


def test_mapping_entry_sets_only_its_fields() -> None:
    req = _builder().near_vector(
        near_vector=[1.0, 0.0, 0.0],
        vector_search_params={"title": VectorSearchParams(filter_strategy="sweeping")},
    )
    (entry,) = req.vector_search_params_for_targets
    assert entry.target == "title"
    assert entry.params.filter_strategy == search_get_pb2.FILTER_STRATEGY_SWEEPING
    assert not entry.params.HasField("ef")
    assert not entry.params.HasField("search_probe")


def test_mapping_entry_with_nothing_set_is_sent() -> None:
    # The server accepts and ignores an empty entry; the client does not drop or reject it.
    req = _builder().near_vector(
        near_vector=[1.0, 0.0, 0.0], vector_search_params={"title": VectorSearchParams()}
    )
    (entry,) = req.vector_search_params_for_targets
    assert entry.target == "title"
    assert entry.HasField("params")


def test_empty_mapping_sends_neither_field() -> None:
    req = _builder().near_vector(near_vector=[1.0, 0.0, 0.0], vector_search_params={})
    assert not req.HasField("vector_search_params")
    assert len(req.vector_search_params_for_targets) == 0


def test_target_names_are_not_validated_client_side() -> None:
    # Unknown / duplicated target names are the server's to reject so the error text has one source.
    req = _builder().near_vector(
        near_vector=[1.0, 0.0, 0.0],
        target_vector=["title"],
        vector_search_params={"not_a_target": VectorSearchParams(ef=8)},
    )
    assert req.vector_search_params_for_targets[0].target == "not_a_target"


@pytest.mark.parametrize(
    "bad",
    [
        {"title": {"ef": 64}},
        {"title": 64},
        {"title": None},
        {1: VectorSearchParams(ef=64)},
        {None: VectorSearchParams(ef=64)},
    ],
    ids=["dict-value", "int-value", "none-value", "int-key", "none-key"],
)
def test_mapping_with_wrong_types_rejected_client_side(bad: object) -> None:
    with pytest.raises(WeaviateInvalidInputError, match="vector_search_params"):
        _builder().near_vector(near_vector=[1.0, 0.0, 0.0], vector_search_params=bad)  # type: ignore[arg-type]


def test_mapping_other_fields_untouched() -> None:
    with_params = _builder().near_vector(
        near_vector=[1.0, 0.0, 0.0],
        limit=5,
        target_vector=["title", "body"],
        vector_search_params={"title": VectorSearchParams(ef=64)},
    )
    without = _builder().near_vector(
        near_vector=[1.0, 0.0, 0.0], limit=5, target_vector=["title", "body"]
    )
    with_params.ClearField("vector_search_params_for_targets")
    assert with_params.SerializeToString(deterministic=True) == without.SerializeToString(
        deterministic=True
    )
