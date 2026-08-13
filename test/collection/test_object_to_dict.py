import datetime
import uuid

from weaviate.collections.classes.internal import (
    CrossReference,
    MetadataReturn,
    Object,
)


def test_object_to_dict_basic() -> None:
    """A plain object with no references should round-trip into a JSON-serializable dict."""
    obj_uuid = uuid.uuid4()
    obj = Object(
        uuid=obj_uuid,
        metadata=MetadataReturn(),
        properties={"name": "Alice", "age": 30},
        references=None,
        vector={},
        collection="Person",
    )

    result = obj.to_dict()

    assert result == {
        "uuid": str(obj_uuid),
        "metadata": {
            "creation_time": None,
            "last_update_time": None,
            "distance": None,
            "certainty": None,
            "score": None,
            "explain_score": None,
            "is_consistent": None,
            "rerank_score": None,
        },
        "properties": {"name": "Alice", "age": 30},
        "references": {},
        "vector": {},
        "collection": "Person",
    }


def test_object_to_dict_converts_datetime_and_uuid_properties() -> None:
    """`datetime` and `UUID` property values are not JSON-serializable by default and must be
    converted to strings."""
    created = datetime.datetime(2024, 2, 16, 12, 0, 0, tzinfo=datetime.timezone.utc)
    friend_id = uuid.uuid4()
    obj = Object(
        uuid=uuid.uuid4(),
        metadata=MetadataReturn(creation_time=created),
        properties={"createdAt": created, "friendId": friend_id},
        references=None,
        vector={"default": [0.1, 0.2, 0.3]},
        collection="Person",
    )

    result = obj.to_dict()

    assert result["properties"]["createdAt"] == created.isoformat()
    assert result["properties"]["friendId"] == str(friend_id)
    assert result["metadata"]["creation_time"] == created.isoformat()
    assert result["vector"] == {"default": [0.1, 0.2, 0.3]}


def test_object_to_dict_expands_cross_references() -> None:
    """Cross-referenced objects are recursively expanded into nested dicts rather than being
    left as opaque `_CrossReference` instances."""
    referenced_uuid = uuid.uuid4()
    referenced_obj = Object(
        uuid=referenced_uuid,
        metadata=MetadataReturn(),
        properties={"title": "Referenced"},
        references=None,
        vector={},
        collection="Article",
    )
    obj = Object(
        uuid=uuid.uuid4(),
        metadata=MetadataReturn(),
        properties={"name": "Bob"},
        references={"wrote": CrossReference([referenced_obj])},
        vector={},
        collection="Person",
    )

    result = obj.to_dict()

    assert result["references"] == {
        "wrote": [
            {
                "uuid": str(referenced_uuid),
                "metadata": {
                    "creation_time": None,
                    "last_update_time": None,
                    "distance": None,
                    "certainty": None,
                    "score": None,
                    "explain_score": None,
                    "is_consistent": None,
                    "rerank_score": None,
                },
                "properties": {"title": "Referenced"},
                "references": {},
                "vector": {},
                "collection": "Article",
            }
        ]
    }


def test_cross_reference_repr_is_human_readable() -> None:
    """`repr()` of a `_CrossReference` should show its objects instead of a bare memory address."""
    referenced_obj = Object(
        uuid=uuid.uuid4(),
        metadata=MetadataReturn(),
        properties={"title": "Referenced"},
        references=None,
        vector={},
        collection="Article",
    )
    ref = CrossReference([referenced_obj])

    result = repr(ref)

    assert result == f"CrossReference(objects={[referenced_obj]!r})"
    assert "object at 0x" not in result
