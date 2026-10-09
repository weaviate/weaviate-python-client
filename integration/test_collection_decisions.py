import pytest

import weaviate.classes as wvc
from weaviate.collections.classes.config import Decisions
from weaviate.exceptions import WeaviateQueryError

from .conftest import CollectionFactory

# decisions-dummy answers from the document text alone, see the module in the server repo:
#   predicate: share of the instruction words found in the text
#   choice: the first option named in the text, else the first option
#   score: text length modulo the number of levels
#   instructions "refuse": refused


def _collection(collection_factory: CollectionFactory):  # type: ignore[no-untyped-def]
    collection = collection_factory(
        decisions_config=wvc.config.Configure.Decisions.custom("decisions-dummy"),
        vectorizer_config=wvc.config.Configure.Vectorizer.none(),
        properties=[wvc.config.Property(name="text", data_type=wvc.config.DataType.TEXT)],
    )
    if "decisions-dummy" not in collection._connection.get_meta()["modules"]:
        pytest.skip("the server has no decisions-dummy module")
    return collection


def test_decisions_config_round_trip(collection_factory: CollectionFactory) -> None:
    collection = _collection(collection_factory)

    config = collection.config.get()
    assert config.reranker_config is None
    assert config.decisions_config is not None
    assert config.decisions_config.decisions == "decisions-dummy"

    collection.config.update(
        decisions_config=wvc.config.Reconfigure.Decisions.typesafeai(cache=False)
    )
    config = collection.config.get()
    assert config.decisions_config is not None
    assert config.decisions_config.decisions == Decisions.TYPESAFEAI
    assert config.decisions_config.model == {"cache": False}

    collection.config.update(
        reranker_config=wvc.config.Reconfigure.Reranker.custom("reranker-dummy")
    )
    config = collection.config.get()
    assert config.decisions_config is None
    assert config.reranker_config is not None
    assert config.reranker_config.reranker == "reranker-dummy"


def test_decide_with_every_kind_of_question(collection_factory: CollectionFactory) -> None:
    collection = _collection(collection_factory)
    collection.data.insert_many(
        [{"text": "the customer is angry about billing"}, {"text": "all good, thanks"}]
    )
    questions = [
        wvc.query.Decide.predicate("angry", prop="text", instructions="customer angry"),
        wvc.query.Decide.choice(
            "team", prop="text", instructions="which team", options={"billing": None, "other": None}
        ),
        wvc.query.Decide.score(
            "length", prop="text", instructions="how long", levels=["short", "medium", "long"]
        ),
        wvc.query.Decide.predicate("no", prop="text", instructions="refuse"),
    ]

    for query in (
        lambda: collection.query.bm25("billing good", decide=questions),
        lambda: collection.query.fetch_objects(decide=questions),
        lambda: collection.query.hybrid("billing good", alpha=0, decide=questions),
    ):
        objs = sorted(query().objects, key=lambda o: str(o.properties["text"]))
        assert len(objs) == 2
        angry, fine = objs[1], objs[0]
        assert angry.decisions is not None and fine.decisions is not None
        assert angry.decisions["angry"].probability == 1.0
        assert fine.decisions["angry"].probability == 0.0
        assert angry.decisions["team"].choice == "billing"
        assert angry.decisions["team"].probabilities == {"billing": 1.0, "other": 0.0}
        assert angry.decisions["team"].confidence == 1.0
        assert fine.decisions["team"].choice == "billing"
        assert angry.decisions["length"].score == float(
            len("the customer is angry about billing") % 3
        )
        assert fine.decisions["length"].score == float(len("all good, thanks") % 3)
        assert angry.decisions["length"].probabilities is not None
        assert set(angry.decisions["length"].probabilities) == {"short", "medium", "long"}
        assert angry.decisions["no"].refused
        assert angry.decisions["no"].probability is None

    objs = collection.query.bm25("billing", decide=questions[0]).objects
    assert objs[0].decisions is not None
    assert list(objs[0].decisions) == ["angry"]


def test_decide_and_rerank_together(collection_factory: CollectionFactory) -> None:
    collection = _collection(collection_factory)
    collection.data.insert_many([{"text": "short"}, {"text": "a much longer document"}])

    objs = collection.query.bm25(
        "short document",
        rerank=wvc.query.Rerank(prop="text", query="anything"),
        decide=wvc.query.Decide.predicate("long", prop="text", instructions="longer"),
    ).objects

    assert [o.properties["text"] for o in objs] == ["a much longer document", "short"]
    assert [o.metadata.rerank_score for o in objs] == [
        float(len("a much longer document")),
        float(len("short")),
    ]
    assert [o.decisions["long"].probability for o in objs if o.decisions] == [1.0, 0.0]


def test_decide_is_rejected_with_group_by(collection_factory: CollectionFactory) -> None:
    collection = _collection(collection_factory)
    collection.data.insert({"text": "x"})

    with pytest.raises(WeaviateQueryError):
        collection.query.bm25(
            "x",
            group_by=wvc.query.GroupBy(prop="text", objects_per_group=1, number_of_groups=1),
            decide=wvc.query.Decide.predicate("q", prop="text", instructions="i"),
        )


def test_decide_without_a_decisions_module(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=wvc.config.Configure.Vectorizer.none(),
        properties=[wvc.config.Property(name="text", data_type=wvc.config.DataType.TEXT)],
    )
    if "decisions-dummy" not in collection._connection.get_meta()["modules"]:
        pytest.skip("the server has no decisions-dummy module")
    collection.data.insert({"text": "x"})

    with pytest.raises(WeaviateQueryError):
        collection.query.bm25(
            "x", decide=wvc.query.Decide.predicate("q", prop="text", instructions="i")
        )
