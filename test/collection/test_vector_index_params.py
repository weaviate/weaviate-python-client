"""Unit tests: ``vector_index_params`` is wired into the two ``SearchRequest`` wire fields.

A single ``VectorIndexParams`` lands in ``vector_index_params`` (request-wide); a mapping keyed by
target vector name becomes one ``vector_index_params_for_targets`` entry each. These tests pin the
request-building contract only: the fields are set exactly when the caller passes them, an omitted
option leaves the request byte-identical to before the option existed, and the client validates
only what the wire format cannot express (types, sign, unknown strategy names); caps, target-name
checks and the bm25 rule stay server-side so their error text comes from one place.
"""

from typing import Callable, Union

import pytest
from pydantic import ValidationError

from weaviate.classes.config import VectorFilterStrategy
from weaviate.classes.query import HybridVector, VectorIndexParams
from weaviate.collections.classes.grpc import _VectorIndexParams
from weaviate.collections.grpc.query import _QueryGRPC
from weaviate.exceptions import WeaviateInvalidInputError, WeaviateUnsupportedFeatureError
from weaviate.proto.v1 import search_get_pb2
from weaviate.util import _ServerVersion

_UUID = "00000000-0000-0000-0000-000000000001"
_DEFAULT_VERSION = _ServerVersion(1, 42, 0)


def _builder(
    version: _ServerVersion = _DEFAULT_VERSION, validate_arguments: bool = True
) -> _QueryGRPC:
    return _QueryGRPC(
        weaviate_version=version,
        name="Dummy",
        tenant=None,
        consistency_level=None,
        validate_arguments=validate_arguments,
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
    req = build(_builder(), {"vector_index_params": VectorIndexParams.hnsw(ef=64)})
    assert req.HasField("vector_index_params")
    assert req.vector_index_params.HasField("ef")
    assert req.vector_index_params.ef == 64


@pytest.mark.parametrize("build", _VECTOR_SEARCHES.values(), ids=_VECTOR_SEARCHES.keys())
def test_field_absent_when_not_given(
    build: Callable[[_QueryGRPC, dict], search_get_pb2.SearchRequest],
) -> None:
    req = build(_builder(), {})
    assert not req.HasField("vector_index_params")


@pytest.mark.parametrize("build", _VECTOR_SEARCHES.values(), ids=_VECTOR_SEARCHES.keys())
def test_none_is_byte_identical_to_omitting(
    build: Callable[[_QueryGRPC, dict], search_get_pb2.SearchRequest],
) -> None:
    omitted = build(_builder(), {})
    explicit_none = build(_builder(), {"vector_index_params": None})
    assert explicit_none.SerializeToString(deterministic=True) == omitted.SerializeToString(
        deterministic=True
    )


def test_params_without_fields_send_an_empty_message() -> None:
    # The server reads every unset field as "use the collection default".
    req = _builder().near_vector(
        near_vector=[1.0, 0.0, 0.0], vector_index_params=VectorIndexParams.hnsw()
    )
    assert req.HasField("vector_index_params")
    assert not req.vector_index_params.HasField("ef")
    assert not req.vector_index_params.HasField("search_probe")
    assert not req.vector_index_params.HasField("filter_strategy")
    assert len(req.vector_index_params_for_targets) == 0


def test_explicit_zero_is_sent_as_zero() -> None:
    # 0 is a legal wire value meaning "collection default"; the client does not drop it.
    req = _builder().near_vector(
        near_vector=[1.0, 0.0, 0.0], vector_index_params=VectorIndexParams.hnsw(ef=0)
    )
    assert req.vector_index_params.HasField("ef")
    assert req.vector_index_params.ef == 0


def test_ef_below_limit_is_sent_unchanged() -> None:
    # Flooring ef at k is the server's job (max(ef, k)); the client must not second-guess it.
    req = _builder().near_vector(
        near_vector=[1.0, 0.0, 0.0], limit=10, vector_index_params=VectorIndexParams.hnsw(ef=2)
    )
    assert req.limit == 10
    assert req.vector_index_params.ef == 2


def test_other_fields_untouched_by_ef() -> None:
    with_ef = _builder().near_vector(
        near_vector=[1.0, 0.0, 0.0], limit=5, vector_index_params=VectorIndexParams.hnsw(ef=64)
    )
    without = _builder().near_vector(near_vector=[1.0, 0.0, 0.0], limit=5)
    with_ef.ClearField("vector_index_params")
    assert with_ef.SerializeToString(deterministic=True) == without.SerializeToString(
        deterministic=True
    )


@pytest.mark.parametrize("bad", [{"ef": 64}, 64, "64", (64,)])
def test_wrong_type_rejected_client_side(bad: object) -> None:
    with pytest.raises(WeaviateInvalidInputError):
        _builder().near_vector(near_vector=[1.0, 0.0, 0.0], vector_index_params=bad)  # type: ignore[arg-type]


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
        VectorIndexParams.hnsw(ef=bad_ef)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "field,bad",
    [
        ("ef", -5),
        ("ef", 2**32),
        ("ef", "64"),
        ("search_probe", -1),
        ("search_probe", 1.5),
        ("filter_strategy", "ACORN"),
    ],
)
def test_assignment_is_validated(field: str, bad: object) -> None:
    # Without validate_assignment a bad value would only surface at query time as a bare protobuf
    # ValueError (or be sent as-is).
    params = VectorIndexParams.hnsw(ef=1)
    with pytest.raises(ValidationError):
        setattr(params, field, bad)
    assert params == VectorIndexParams.hnsw(ef=1)


def test_valid_assignment_is_sent() -> None:
    params = VectorIndexParams.hnsw(ef=1)
    params.ef = 64
    params.filter_strategy = VectorFilterStrategy.ACORN
    req = _builder().near_vector(near_vector=[1.0, 0.0, 0.0], vector_index_params=params)
    assert req.vector_index_params.ef == 64
    assert req.vector_index_params.filter_strategy == search_get_pb2.FILTER_STRATEGY_ACORN


def test_unknown_field_assignment_rejected() -> None:
    params = VectorIndexParams.hnsw()
    with pytest.raises(ValueError):
        params.efConstruction = 3  # type: ignore[attr-defined]


def test_uint32_max_is_sent_for_the_server_to_reject() -> None:
    # The last representable value is legal on the wire; the HNSW_MAX_SEARCH_EF cap is the server's.
    req = _builder().near_vector(
        near_vector=[1.0, 0.0, 0.0], vector_index_params=VectorIndexParams.hnsw(ef=2**32 - 1)
    )
    assert req.vector_index_params.ef == 2**32 - 1


def test_unknown_params_rejected() -> None:
    # Keeps a typo (or a knob that only exists in the collection config) from being silently dropped.
    with pytest.raises(ValidationError):
        _VectorIndexParams(efConstruction=3)  # type: ignore[call-arg]


def test_not_offered_on_keyword_only_searches() -> None:
    # The server rejects vector_index_params on bm25-only requests and it is meaningless for
    # fetch_objects, so neither builder accepts the keyword.
    with pytest.raises(TypeError):
        _builder().bm25(query="cats", vector_index_params=VectorIndexParams.hnsw(ef=64))  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        _builder().get(vector_index_params=VectorIndexParams.hnsw(ef=64))  # type: ignore[call-arg]


@pytest.mark.parametrize("build", _VECTOR_SEARCHES.values(), ids=_VECTOR_SEARCHES.keys())
def test_rejected_on_servers_without_the_feature(
    build: Callable[[_QueryGRPC, dict], search_get_pb2.SearchRequest],
) -> None:
    # A pre-1.42 server would drop the unknown field and silently search with the collection ef.
    with pytest.raises(WeaviateUnsupportedFeatureError, match="1.42.0"):
        build(
            _builder(_ServerVersion(1, 41, 0)),
            {"vector_index_params": VectorIndexParams.hnsw(ef=64)},
        )


def test_mapping_rejected_on_servers_without_the_feature() -> None:
    with pytest.raises(WeaviateUnsupportedFeatureError, match="1.42.0"):
        _builder(_ServerVersion(1, 41, 0)).near_vector(
            near_vector=[1.0, 0.0, 0.0],
            vector_index_params={"title": VectorIndexParams.hnsw(ef=64)},
        )


def test_old_server_fine_without_the_option() -> None:
    req = _builder(_ServerVersion(1, 41, 0)).near_vector(near_vector=[1.0, 0.0, 0.0])
    assert not req.HasField("vector_index_params")


def test_release_candidate_of_minimum_version_accepted() -> None:
    req = _builder(_ServerVersion.from_string("1.42.0-rc.0")).near_vector(
        near_vector=[1.0, 0.0, 0.0], vector_index_params=VectorIndexParams.hnsw(ef=64)
    )
    assert req.vector_index_params.ef == 64


# --- all knobs on one message ---------------------------------------------------------------


def test_all_fields_are_sent_together() -> None:
    # The wire model carries every knob; only the public constructors keep them apart per index.
    req = _builder().near_vector(
        near_vector=[1.0, 0.0, 0.0],
        vector_index_params=_VectorIndexParams(
            ef=64, search_probe=8, filter_strategy=VectorFilterStrategy.ACORN
        ),
    )
    params = req.vector_index_params
    assert params.ef == 64
    assert params.search_probe == 8
    assert params.filter_strategy == search_get_pb2.FILTER_STRATEGY_ACORN


def test_search_probe_alone_leaves_hnsw_fields_unset() -> None:
    req = _builder().near_vector(
        near_vector=[1.0, 0.0, 0.0], vector_index_params=VectorIndexParams.hfresh(search_probe=3)
    )
    params = req.vector_index_params
    assert params.HasField("search_probe") and params.search_probe == 3
    assert not params.HasField("ef")
    assert not params.HasField("filter_strategy")


@pytest.mark.parametrize(
    "name,expected",
    [
        ("sweeping", search_get_pb2.FILTER_STRATEGY_SWEEPING),
        ("acorn", search_get_pb2.FILTER_STRATEGY_ACORN),
        ("pathseer", search_get_pb2.FILTER_STRATEGY_PATHSEER),
        (VectorFilterStrategy.SWEEPING, search_get_pb2.FILTER_STRATEGY_SWEEPING),
        (VectorFilterStrategy.ACORN, search_get_pb2.FILTER_STRATEGY_ACORN),
        (VectorFilterStrategy.PATHSEER, search_get_pb2.FILTER_STRATEGY_PATHSEER),
    ],
)
def test_filter_strategy_maps_to_enum(
    name: Union[str, VectorFilterStrategy], expected: int
) -> None:
    # Plain strings are accepted at runtime (pydantic coerces them to the enum) even though the
    # annotation names the enum; both spellings must reach the wire as the same value.
    req = _builder().near_vector(
        near_vector=[1.0, 0.0, 0.0],
        vector_index_params=VectorIndexParams.hnsw(filter_strategy=name),  # type: ignore[arg-type]
    )
    assert req.vector_index_params.HasField("filter_strategy")
    assert req.vector_index_params.filter_strategy == expected
    # UNSPECIFIED is never sent explicitly: None leaves the field unset instead.
    assert expected != search_get_pb2.FILTER_STRATEGY_UNSPECIFIED


@pytest.mark.parametrize("bad", ["ACORN", "Acorn", "unspecified", "", 1, True])
def test_unknown_filter_strategy_rejected_client_side(bad: object) -> None:
    # Cheap to check here; the server would also answer InvalidArgument for an unknown enum value.
    with pytest.raises(ValidationError):
        VectorIndexParams.hnsw(filter_strategy=bad)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "bad",
    [-1, 2**32, True, "8", 1.5],
    ids=["negative", "above-uint32", "bool", "str", "float"],
)
def test_search_probe_must_be_a_uint32(bad: object) -> None:
    with pytest.raises(ValidationError):
        VectorIndexParams.hfresh(search_probe=bad)  # type: ignore[arg-type]


# --- constructors --------------------------------------------------------------------------


def test_hnsw_constructor_sets_only_hnsw_knobs() -> None:
    params = VectorIndexParams.hnsw(ef=32, filter_strategy=VectorFilterStrategy.PATHSEER)
    assert params == _VectorIndexParams(ef=32, filter_strategy=VectorFilterStrategy.PATHSEER)
    assert params.search_probe is None
    assert VectorIndexParams.hnsw() == _VectorIndexParams()


def test_hfresh_constructor_sets_only_search_probe() -> None:
    params = VectorIndexParams.hfresh(search_probe=12)
    assert params == _VectorIndexParams(search_probe=12)
    assert params.ef is None and params.filter_strategy is None
    assert VectorIndexParams.hfresh() == _VectorIndexParams()


def test_cannot_be_instantiated_directly() -> None:
    # Only the constructors build params, so a caller cannot combine knobs of different index
    # types (``hnsw`` has no ``search_probe``, ``hfresh`` no ``ef``) or skip the typed entry point.
    with pytest.raises(TypeError, match="VectorIndexParams.hnsw"):
        VectorIndexParams()
    with pytest.raises(TypeError, match="VectorIndexParams.hnsw"):
        VectorIndexParams(ef=1)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        VectorIndexParams.hnsw(search_probe=1)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        VectorIndexParams.hfresh(ef=1)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        VectorIndexParams.hnsw(1)  # type: ignore[misc]


def test_no_dynamic_constructor() -> None:
    # A dynamic index forwards the params to its HNSW stage, so hnsw() already covers it; a
    # separate dynamic() would only be a way to silently drop search_probe.
    assert not hasattr(VectorIndexParams, "dynamic")


@pytest.mark.parametrize("bad", [-1, "32", 1.5])
def test_constructors_validate_like_the_class(bad: object) -> None:
    with pytest.raises(ValidationError):
        VectorIndexParams.hnsw(ef=bad)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        VectorIndexParams.hfresh(search_probe=bad)  # type: ignore[arg-type]


# --- per-target mapping ----------------------------------------------------------------------


@pytest.mark.parametrize("build", _VECTOR_SEARCHES.values(), ids=_VECTOR_SEARCHES.keys())
def test_mapping_becomes_per_target_entries_and_no_request_wide_field(
    build: Callable[[_QueryGRPC, dict], search_get_pb2.SearchRequest],
) -> None:
    req = build(
        _builder(),
        {
            "vector_index_params": {
                "title": VectorIndexParams.hnsw(ef=16),
                "body": VectorIndexParams.hfresh(search_probe=4),
            }
        },
    )
    assert not req.HasField("vector_index_params")
    by_target = {e.target: e.params for e in req.vector_index_params_for_targets}
    assert set(by_target) == {"title", "body"}
    assert by_target["title"].ef == 16
    assert not by_target["title"].HasField("search_probe")
    assert by_target["body"].search_probe == 4
    assert not by_target["body"].HasField("ef")


def test_mapping_preserves_insertion_order() -> None:
    req = _builder().near_vector(
        near_vector=[1.0, 0.0, 0.0],
        vector_index_params={
            "c": VectorIndexParams.hnsw(ef=3),
            "a": VectorIndexParams.hnsw(ef=1),
            "b": VectorIndexParams.hnsw(ef=2),
        },
    )
    assert [e.target for e in req.vector_index_params_for_targets] == ["c", "a", "b"]


def test_mapping_entry_sets_only_its_fields() -> None:
    req = _builder().near_vector(
        near_vector=[1.0, 0.0, 0.0],
        vector_index_params={
            "title": VectorIndexParams.hnsw(filter_strategy=VectorFilterStrategy.SWEEPING)
        },
    )
    (entry,) = req.vector_index_params_for_targets
    assert entry.target == "title"
    assert entry.params.filter_strategy == search_get_pb2.FILTER_STRATEGY_SWEEPING
    assert not entry.params.HasField("ef")
    assert not entry.params.HasField("search_probe")


def test_mapping_entry_with_nothing_set_is_sent() -> None:
    # The server accepts and ignores an empty entry; the client does not drop or reject it.
    req = _builder().near_vector(
        near_vector=[1.0, 0.0, 0.0], vector_index_params={"title": VectorIndexParams.hnsw()}
    )
    (entry,) = req.vector_index_params_for_targets
    assert entry.target == "title"
    assert entry.HasField("params")


@pytest.mark.parametrize(
    "version",
    [_ServerVersion(1, 41, 0), _ServerVersion(1, 42, 0)],
    ids=["below-1.42", "1.42"],
)
@pytest.mark.parametrize("build", _VECTOR_SEARCHES.values(), ids=_VECTOR_SEARCHES.keys())
def test_empty_mapping_behaves_like_none(
    build: Callable[[_QueryGRPC, dict], search_get_pb2.SearchRequest], version: _ServerVersion
) -> None:
    # An empty mapping tunes nothing, so it must neither send a field nor trip the version gate.
    omitted = build(_builder(version), {})
    empty = build(_builder(version), {"vector_index_params": {}})
    assert not empty.HasField("vector_index_params")
    assert len(empty.vector_index_params_for_targets) == 0
    assert empty.SerializeToString(deterministic=True) == omitted.SerializeToString(
        deterministic=True
    )


def test_target_names_are_not_validated_client_side() -> None:
    # Unknown / duplicated target names are the server's to reject so the error text has one source.
    req = _builder().near_vector(
        near_vector=[1.0, 0.0, 0.0],
        target_vector=["title"],
        vector_index_params={"not_a_target": VectorIndexParams.hnsw(ef=8)},
    )
    assert req.vector_index_params_for_targets[0].target == "not_a_target"


@pytest.mark.parametrize(
    "bad",
    [
        {"title": {"ef": 64}},
        {"title": 64},
        {"title": None},
        {1: VectorIndexParams.hnsw(ef=64)},
        {None: VectorIndexParams.hnsw(ef=64)},
    ],
    ids=["dict-value", "int-value", "none-value", "int-key", "none-key"],
)
def test_mapping_with_wrong_types_rejected_client_side(bad: object) -> None:
    with pytest.raises(WeaviateInvalidInputError, match="vector_index_params"):
        _builder().near_vector(near_vector=[1.0, 0.0, 0.0], vector_index_params=bad)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "bad",
    [
        [VectorIndexParams.hnsw(ef=64)],
        (VectorIndexParams.hnsw(ef=64),),
        [],
        64,
        "title",
        {"ef": 64},
    ],
    ids=["list", "tuple", "empty-list", "int", "str", "dict-of-fields"],
)
@pytest.mark.parametrize(
    "version",
    [_ServerVersion(1, 41, 0), _ServerVersion(1, 42, 0)],
    ids=["below-1.42", "1.42"],
)
def test_wrong_type_rejected_without_argument_validation(
    bad: object, version: _ServerVersion
) -> None:
    # validate_arguments=False skips _ValidateArgument; the mapping code must still not crash with
    # an AttributeError on a non-Mapping.
    with pytest.raises(WeaviateInvalidInputError, match="vector_index_params"):
        _builder(version, validate_arguments=False).near_vector(
            near_vector=[1.0, 0.0, 0.0],
            vector_index_params=bad,  # type: ignore[arg-type]
        )


def test_mapping_other_fields_untouched() -> None:
    with_params = _builder().near_vector(
        near_vector=[1.0, 0.0, 0.0],
        limit=5,
        target_vector=["title", "body"],
        vector_index_params={"title": VectorIndexParams.hnsw(ef=64)},
    )
    without = _builder().near_vector(
        near_vector=[1.0, 0.0, 0.0], limit=5, target_vector=["title", "body"]
    )
    with_params.ClearField("vector_index_params_for_targets")
    assert with_params.SerializeToString(deterministic=True) == without.SerializeToString(
        deterministic=True
    )


def test_public_types_are_exported() -> None:
    # Callers annotating a strategy or a params argument held in a variable need these names.
    import weaviate.classes.query as query
    from weaviate.collections.classes import grpc

    for name in ("VectorIndexParams", "VectorIndexParamsReturn", "VectorIndexParamsType"):
        assert name in query.__all__
        assert getattr(query, name) is getattr(grpc, name)
