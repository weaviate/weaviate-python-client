import pytest

import weaviate.classes as wvc
from weaviate.collections.classes.config import Decisions
from weaviate.exceptions import WeaviateInvalidInputError, WeaviateQueryError

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
        decisions_config=wvc.config.Reconfigure.Decisions.typesafeai(min_probability=0.5)
    )
    config = collection.config.get()
    assert config.decisions_config is not None
    assert config.decisions_config.decisions == Decisions.TYPESAFEAI
    assert config.decisions_config.model == {"minProbability": 0.5}

    # A reranker joins the decisions module; an update replaces a module of its own kind only.
    collection.config.update(
        reranker_config=wvc.config.Reconfigure.Reranker.custom("reranker-dummy")
    )
    config = collection.config.get()
    assert config.decisions_config is not None
    assert config.decisions_config.decisions == Decisions.TYPESAFEAI
    assert config.reranker_config is not None
    assert config.reranker_config.reranker == "reranker-dummy"


def test_annotate_with_every_kind_of_question(collection_factory: CollectionFactory) -> None:
    collection = _collection(collection_factory)
    collection.data.insert_many(
        [{"text": "the customer is angry about billing"}, {"text": "all good, thanks"}]
    )
    questions = [
        wvc.query.Decision.predicate("angry", prop="text", instructions="customer angry"),
        wvc.query.Decision.choice(
            "team", prop="text", instructions="which team", options={"billing": None, "other": None}
        ),
        wvc.query.Decision.score(
            "length", prop="text", instructions="how long", levels=["short", "medium", "long"]
        ),
        wvc.query.Decision.predicate("no", prop="text", instructions="refuse"),
    ]

    for query in (
        lambda: collection.query.bm25("billing good", annotate=questions),
        lambda: collection.query.fetch_objects(annotate=questions),
        lambda: collection.query.hybrid("billing good", alpha=0, annotate=questions),
    ):
        objs = sorted(query().objects, key=lambda o: str(o.properties["text"]))
        assert len(objs) == 2
        angry, fine = objs[1], objs[0]
        assert angry.annotations is not None and fine.annotations is not None
        assert angry.annotations["angry"].probability == 1.0
        assert fine.annotations["angry"].probability == 0.0
        assert angry.annotations["team"].choice == "billing"
        assert angry.annotations["team"].probabilities == {"billing": 1.0, "other": 0.0}
        assert angry.annotations["team"].confidence == 1.0
        assert fine.annotations["team"].choice == "billing"
        assert angry.annotations["length"].score == float(
            len("the customer is angry about billing") % 3
        )
        assert fine.annotations["length"].score == float(len("all good, thanks") % 3)
        assert angry.annotations["length"].probabilities is not None
        assert set(angry.annotations["length"].probabilities) == {"short", "medium", "long"}
        assert angry.annotations["no"].refused
        assert angry.annotations["no"].probability is None

    objs = collection.query.bm25("billing", annotate=questions[0]).objects
    assert objs[0].annotations is not None
    assert list(objs[0].annotations) == ["angry"]


ANGRY = "the customer is angry about billing"
CALM = "all good, thanks"


def _texts(objs) -> list:  # type: ignore[no-untyped-def]
    return [o.properties["text"] for o in objs]


# A keyword search that returns both texts: rerank goes with a search, not
# with fetch_objects.
SEARCH = "customer good"


def test_rerank_by_a_decision(collection_factory: CollectionFactory) -> None:
    collection = _collection(collection_factory)
    collection.data.insert_many([{"text": ANGRY}, {"text": CALM}])

    # The class settings are the defaults: search order, nothing dropped.
    objs = collection.query.bm25(
        SEARCH, rerank=wvc.query.Rerank.decide(prop="text", query="customer angry")
    ).objects
    assert {o.properties["text"]: o.metadata.rerank_score for o in objs} == {ANGRY: 1.0, CALM: 0.0}

    # A threshold drops the candidates below it.
    objs = collection.query.bm25(
        SEARCH,
        rerank=wvc.query.Rerank.decide(prop="text", query="customer angry", min_probability=0.6),
    ).objects
    assert _texts(objs) == [ANGRY]
    assert objs[0].metadata.rerank_score == 1.0

    # "all good, thanks" matches two of three words, the angry text one.
    objs = collection.query.bm25(
        SEARCH,
        rerank=wvc.query.Rerank.decide(
            prop="text",
            query="good thanks customer",
            min_probability=0.3,
            order=wvc.query.DecisionsOrder.PROBABILITY,
        ),
    ).objects
    assert _texts(objs) == [CALM, ANGRY]

    # A plain rerank on a class with only a decisions module is a relevance predicate.
    objs = collection.query.bm25(
        SEARCH, rerank=wvc.query.Rerank(prop="text", query="customer angry")
    ).objects
    assert {o.properties["text"]: o.metadata.rerank_score for o in objs} == {ANGRY: 1.0, CALM: 0.0}


def test_rerank_by_a_decision_takes_the_class_settings(
    collection_factory: CollectionFactory,
) -> None:
    collection = collection_factory(
        decisions_config=wvc.config.Configure.Decisions.custom(
            "decisions-dummy", {"minProbability": 0.9, "order": "probability"}
        ),
        vectorizer_config=wvc.config.Configure.Vectorizer.none(),
        properties=[wvc.config.Property(name="text", data_type=wvc.config.DataType.TEXT)],
    )
    if "decisions-dummy" not in collection._connection.get_meta()["modules"]:
        pytest.skip("the server has no decisions-dummy module")
    collection.data.insert_many([{"text": ANGRY}, {"text": CALM}])

    objs = collection.query.bm25(
        SEARCH, rerank=wvc.query.Rerank.decide(prop="text", query="good thanks customer")
    ).objects
    assert objs == [], "no text has every word"

    # The request overrides the threshold; the class order still applies.
    objs = collection.query.bm25(
        SEARCH,
        rerank=wvc.query.Rerank.decide(
            prop="text", query="good thanks customer", min_probability=0.3
        ),
    ).objects
    assert _texts(objs) == [CALM, ANGRY]


def test_rerank_by_a_decision_without_a_decisions_module(
    collection_factory: CollectionFactory,
) -> None:
    collection = collection_factory(
        reranker_config=wvc.config.Configure.Reranker.custom("reranker-dummy"),
        vectorizer_config=wvc.config.Configure.Vectorizer.none(),
        properties=[wvc.config.Property(name="text", data_type=wvc.config.DataType.TEXT)],
    )
    if "decisions-dummy" not in collection._connection.get_meta()["modules"]:
        pytest.skip("the server has no decisions-dummy module")
    collection.data.insert({"text": "x"})

    # The server rejects it before the search.
    with pytest.raises(WeaviateQueryError, match="no decisions module"):
        collection.query.bm25("x", rerank=wvc.query.Rerank.decide(prop="text", query="x"))


def test_a_reranker_and_a_decisions_module_on_one_collection(
    collection_factory: CollectionFactory,
) -> None:
    collection = collection_factory(
        reranker_config=wvc.config.Configure.Reranker.custom("reranker-dummy"),
        decisions_config=wvc.config.Configure.Decisions.custom("decisions-dummy"),
        vectorizer_config=wvc.config.Configure.Vectorizer.none(),
        properties=[wvc.config.Property(name="text", data_type=wvc.config.DataType.TEXT)],
    )
    if "decisions-dummy" not in collection._connection.get_meta()["modules"]:
        pytest.skip("the server has no decisions-dummy module")
    collection.data.insert_many([{"text": ANGRY}, {"text": CALM}])

    # A plain rerank goes to the reranker, which scores by length; annotate goes to the
    # decisions module.
    objs = collection.query.bm25(
        "billing good",
        rerank=wvc.query.Rerank(prop="text", query="customer angry"),
        annotate=wvc.query.Decision.predicate("angry", prop="text", instructions="customer angry"),
    ).objects
    assert _texts(objs) == [ANGRY, CALM]
    assert [o.metadata.rerank_score for o in objs] == [float(len(ANGRY)), float(len(CALM))]
    assert [o.annotations["angry"].probability for o in objs if o.annotations] == [1.0, 0.0]

    # A decision goes to the decisions module: the probability is the score.
    objs = collection.query.bm25(
        "billing good",
        rerank=wvc.query.Rerank.decide(prop="text", query="customer angry", min_probability=0.6),
    ).objects
    assert _texts(objs) == [ANGRY]
    assert objs[0].metadata.rerank_score == 1.0


def test_annotate_is_rejected_with_group_by(collection_factory: CollectionFactory) -> None:
    collection = _collection(collection_factory)
    collection.data.insert({"text": "x"})

    # The client refuses it before the request, as the server would.
    with pytest.raises(WeaviateInvalidInputError):
        collection.query.bm25(
            "x",
            group_by=wvc.query.GroupBy(prop="text", objects_per_group=1, number_of_groups=1),
            annotate=wvc.query.Decision.predicate("q", prop="text", instructions="i"),
        )


def test_annotate_without_a_decisions_module(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=wvc.config.Configure.Vectorizer.none(),
        properties=[wvc.config.Property(name="text", data_type=wvc.config.DataType.TEXT)],
    )
    if "decisions-dummy" not in collection._connection.get_meta()["modules"]:
        pytest.skip("the server has no decisions-dummy module")
    collection.data.insert({"text": "x"})

    with pytest.raises(WeaviateQueryError):
        collection.query.bm25(
            "x", annotate=wvc.query.Decision.predicate("q", prop="text", instructions="i")
        )


# A 1x1 PNG, as a blob property holds it.
PNG = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNgYGAAAAAEAAH2FzhVAAAAAElFTkSuQmCC"


def test_annotate_and_rerank_about_an_image_property(collection_factory: CollectionFactory) -> None:
    # decisions-dummy judges a blob as the text of its base64, so the answer is a
    # probability of 0 for an object with a photo and a refusal for an object without
    # one. A refused candidate stays in a rerank with a score of 0.
    collection = collection_factory(
        decisions_config=wvc.config.Configure.Decisions.custom("decisions-dummy"),
        vectorizer_config=wvc.config.Configure.Vectorizer.none(),
        properties=[
            wvc.config.Property(name="text", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="photo", data_type=wvc.config.DataType.BLOB),
        ],
    )
    if "decisions-dummy" not in collection._connection.get_meta()["modules"]:
        pytest.skip("the server has no decisions-dummy module")
    collection.data.insert_many([{"text": "photo here", "photo": PNG}, {"text": "nothing here"}])

    objs = collection.query.bm25(
        "here",
        annotate=wvc.query.Decision.predicate("damaged", prop="photo", instructions="damaged"),
    ).objects

    by_text = {o.properties["text"]: o.annotations["damaged"] for o in objs if o.annotations}
    assert by_text["photo here"].probability == 0.0
    assert by_text["nothing here"].refused

    objs = collection.query.bm25(
        "here", rerank=wvc.query.Rerank.decide(prop="photo", query="damaged")
    ).objects
    assert {o.properties["text"]: o.metadata.rerank_score for o in objs} == {
        "photo here": 0.0,
        "nothing here": 0.0,
    }


def test_a_provider_named_by_the_query(collection_factory: CollectionFactory) -> None:
    # The collection has no decisions module; the query names one, with a setting for
    # this query only.
    collection = collection_factory(
        vectorizer_config=wvc.config.Configure.Vectorizer.none(),
        properties=[wvc.config.Property(name="text", data_type=wvc.config.DataType.TEXT)],
    )
    if "decisions-dummy" not in collection._connection.get_meta()["modules"]:
        pytest.skip("the server has no decisions-dummy module")
    collection.data.insert_many([{"text": "the customer is angry"}, {"text": "all good"}])
    dummy = wvc.query.DecisionsConfig.custom("decisions-dummy")

    objs = collection.query.bm25(
        "customer good",
        annotate=wvc.query.Decision.predicate("angry", prop="text", instructions="customer angry"),
        annotate_provider=dummy,
    ).objects
    assert {
        o.properties["text"]: o.annotations["angry"].probability for o in objs if o.annotations
    } == {
        "the customer is angry": 1.0,
        "all good": 0.0,
    }

    objs = collection.query.bm25(
        "customer good",
        rerank=wvc.query.Rerank.decide(
            prop="text", query="customer angry", min_probability=0.6, provider=dummy
        ),
    ).objects
    assert [o.properties["text"] for o in objs] == ["the customer is angry"]

    # The request's maxDocuments bounds the page.
    with pytest.raises(WeaviateQueryError, match="maxDocuments 1"):
        collection.query.bm25(
            "customer good",
            limit=2,
            annotate=wvc.query.Decision.predicate(
                "angry", prop="text", instructions="customer angry"
            ),
            annotate_provider=wvc.query.DecisionsConfig.custom(
                "decisions-dummy", {"maxDocuments": 1}
            ),
        )

    # A module that is not enabled fails before the search.
    with pytest.raises(WeaviateQueryError, match="not enabled"):
        collection.query.bm25(
            "customer good",
            annotate=wvc.query.Decision.predicate(
                "angry", prop="text", instructions="customer angry"
            ),
            annotate_provider=wvc.query.DecisionsConfig.custom("decisions-nope"),
        )
