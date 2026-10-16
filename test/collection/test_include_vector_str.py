"""`include_vector` accepts a bare ``str`` but then requests no vector at all.

``INCLUDE_VECTOR = Union[bool, str, List[str]]`` and ``_parse_return_metadata``
validates ``[bool, str, Sequence]``, so a single named vector may be passed as a
string. ``_MetadataQuery.from_public`` only handles ``bool`` and ``list``, so a
string falls through both branches and the gRPC ``MetadataRequest`` asks for
nothing, while ``_QueryOptions`` still reports ``include_vector=True``.
"""

from weaviate.collections.classes.grpc import _MetadataQuery
from weaviate.collections.classes.internal import _QueryOptions


def test_metadata_query_from_public_with_a_list() -> None:
    """Baseline: the list form requests the named vector."""
    md = _MetadataQuery.from_public(None, ["named_vec"])
    assert md.vectors == ["named_vec"]


def test_metadata_query_from_public_with_a_bare_string() -> None:
    md = _MetadataQuery.from_public(None, "named_vec")
    assert md.vectors == ["named_vec"], (
        f"a bare str requested nothing: vector={md.vector!r} vectors={md.vectors!r}"
    )


def test_query_options_and_metadata_query_agree_for_a_bare_string() -> None:
    """The parser is told a vector is coming; the request never asked for one."""
    opts = _QueryOptions.from_input(None, None, "named_vec", None, None)
    md = _MetadataQuery.from_public(None, "named_vec")
    assert opts.include_vector is True
    assert bool(md.vector) or md.vectors, "include_vector=True but nothing was requested"
