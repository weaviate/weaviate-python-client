import pytest
from pydantic import ValidationError

import weaviate
from mock_tests.conftest import MockDecisionsWeaviateService
from weaviate.classes.query import Decision, DecisionsConfig, DecisionsOrder, GroupBy, Rerank
from weaviate.collections.classes.internal import DecisionAnswer
from weaviate.exceptions import WeaviateInvalidInputError
from weaviate.proto.v1 import search_get_pb2

QUESTIONS = [
    Decision.predicate("angry", prop="text", instructions="Is the customer angry?"),
    Decision.choice(
        "team",
        prop="text",
        instructions="Which team should handle this?",
        options={"billing": "money and invoices", "support": None},
    ),
    Decision.score(
        "severity",
        prop="text",
        instructions="How severe is the complaint?",
        levels=["low", "medium", "high"],
    ),
    Decision.predicate("refused", prop="text", instructions="refuse"),
]


def test_annotate_is_sent_and_answers_are_parsed(
    decisions_collection: tuple[weaviate.collections.Collection, MockDecisionsWeaviateService],
) -> None:
    collection, service = decisions_collection

    objs = collection.query.bm25("billing", annotate=QUESTIONS).objects

    sent = service.captured_request.annotate.questions
    assert [q.name for q in sent] == ["angry", "team", "severity", "refused"]
    assert sent[0].property == "text"
    assert sent[0].instructions == "Is the customer angry?"
    assert sent[0].HasField("predicate")
    assert [
        (o.value, o.description if o.HasField("description") else None)
        for o in sent[1].choice.options
    ] == [
        ("billing", "money and invoices"),
        ("support", None),
    ]
    assert [(lvl.label, lvl.HasField("description")) for lvl in sent[2].score.levels] == [
        ("low", False),
        ("medium", False),
        ("high", False),
    ]

    assert len(objs) == 2
    assert objs[0].annotations == {
        "angry": DecisionAnswer(name="angry", probability=0.91),
        "team": DecisionAnswer(
            name="team",
            choice="billing",
            probabilities={"billing": 0.8, "support": 0.2},
            confidence=0.8,
        ),
        "severity": DecisionAnswer(
            name="severity",
            score=2.0,
            probabilities={"low": 0.1, "medium": 0.3, "high": 0.6},
            confidence=0.6,
        ),
        "refused": DecisionAnswer(name="refused", refused=True),
    }
    assert objs[1].annotations is None, "an object without annotations has none"


def test_a_single_question_is_accepted(
    decisions_collection: tuple[weaviate.collections.Collection, MockDecisionsWeaviateService],
) -> None:
    collection, service = decisions_collection

    collection.query.bm25("billing", annotate=QUESTIONS[0])

    assert [q.name for q in service.captured_request.annotate.questions] == ["angry"]


def test_no_annotate_sends_no_questions(
    decisions_collection: tuple[weaviate.collections.Collection, MockDecisionsWeaviateService],
) -> None:
    collection, service = decisions_collection

    objs = collection.query.bm25("billing").objects

    assert not service.captured_request.HasField("annotate")
    assert objs[0].annotations is not None, "the mock answers regardless of the request"


@pytest.mark.parametrize(
    "build",
    [
        lambda: Decision.choice("t", prop="p", instructions="i", options={"only": None}),
        lambda: Decision.choice("t", prop="p", instructions="i", options="ab"),  # type: ignore[arg-type]
        lambda: Decision.score("t", prop="p", instructions="i", levels=["only"]),
        lambda: Decision.score("t", prop="p", instructions="i", levels="ab"),  # type: ignore[arg-type]
        lambda: Decision.choice("t", prop="p", instructions="i", options=["a", "a"]),
        lambda: Decision.score("t", prop="p", instructions="i", levels=["a", "a"]),
    ],
)
def test_questions_need_at_least_two_named_answers(build) -> None:
    with pytest.raises(WeaviateInvalidInputError):
        build()


def test_annotate_is_rejected_before_the_request(
    decisions_collection: tuple[weaviate.collections.Collection, MockDecisionsWeaviateService],
) -> None:
    collection, service = decisions_collection
    service.captured_request = search_get_pb2.SearchRequest()

    with pytest.raises(WeaviateInvalidInputError, match="at least one question"):
        collection.query.bm25("billing", annotate=[])
    with pytest.raises(WeaviateInvalidInputError, match="group_by"):
        collection.query.bm25(
            "billing",
            group_by=GroupBy(prop="text", objects_per_group=1, number_of_groups=1),
            annotate=QUESTIONS[0],
        )
    assert service.captured_request.collection == "", "nothing was sent"


def test_rerank_by_a_decision_is_sent(
    decisions_collection: tuple[weaviate.collections.Collection, MockDecisionsWeaviateService],
) -> None:
    collection, service = decisions_collection

    collection.query.bm25(
        "billing",
        rerank=Rerank.decide(
            prop="text", query="angry", min_probability=0.6, order=DecisionsOrder.PROBABILITY
        ),
    )
    sent = service.captured_request.rerank
    assert sent.property == "text"
    assert sent.query == "angry"
    assert sent.decision.min_probability == 0.6
    assert sent.decision.order == search_get_pb2.RerankOrder.RERANK_ORDER_PROBABILITY

    # Unset options are left unset, so the class settings apply.
    collection.query.bm25("billing", rerank=Rerank.decide(prop="text", query="angry"))
    sent = service.captured_request.rerank
    assert sent.HasField("decision")
    assert not sent.decision.HasField("min_probability")
    assert not sent.decision.HasField("order")

    collection.query.bm25("billing", rerank=Rerank(prop="text", query="angry"))
    assert not service.captured_request.rerank.HasField("decision")


@pytest.mark.parametrize("min_probability", [-0.1, 1.1])
def test_rerank_by_a_decision_needs_a_probability(min_probability: float) -> None:
    with pytest.raises(ValidationError):
        Rerank.decide(prop="text", query="angry", min_probability=min_probability)


@pytest.mark.parametrize("query", [None, "", "   "])
def test_rerank_by_a_decision_needs_a_query(query) -> None:
    with pytest.raises(WeaviateInvalidInputError, match="Rerank.decide needs the query"):
        Rerank.decide(prop="text", query=query)


@pytest.mark.parametrize("order", ["PROBABILITY", "random", 2])
def test_rerank_by_a_decision_names_a_bad_order(order) -> None:
    with pytest.raises(WeaviateInvalidInputError, match="order must be one of"):
        Rerank.decide(prop="text", query="angry", order=order)


def test_rerank_by_a_decision_takes_the_order_as_a_string(
    decisions_collection: tuple[weaviate.collections.Collection, MockDecisionsWeaviateService],
) -> None:
    collection, service = decisions_collection
    order = "probability"

    collection.query.bm25("billing", rerank=Rerank.decide(prop="text", query="angry", order=order))

    assert (
        service.captured_request.rerank.decision.order
        == search_get_pb2.RerankOrder.RERANK_ORDER_PROBABILITY
    )


def test_annotate_provider_is_sent(
    decisions_collection: tuple[weaviate.collections.Collection, MockDecisionsWeaviateService],
) -> None:
    collection, service = decisions_collection

    collection.query.bm25(
        "billing",
        annotate=QUESTIONS[0],
        annotate_provider=DecisionsConfig.typesafeai(
            model="jev-preview", base_url="https://example.test", max_documents=7, images=True
        ),
    )
    sent = service.captured_request.annotate.provider
    assert sent.WhichOneof("kind") == "typesafeai"
    assert sent.typesafeai.model == "jev-preview"
    assert sent.typesafeai.base_url == "https://example.test"
    assert sent.typesafeai.max_documents == 7
    assert sent.typesafeai.images is True

    # An option left out is left unset, so the class setting applies.
    collection.query.bm25(
        "billing",
        annotate=QUESTIONS[0],
        annotate_provider=DecisionsConfig.openai(model="gpt-6-luna"),
    )
    sent = service.captured_request.annotate.provider
    assert sent.WhichOneof("kind") == "openai"
    assert sent.openai.model == "gpt-6-luna"
    assert not sent.openai.HasField("base_url")
    assert not sent.openai.HasField("max_documents")

    collection.query.bm25(
        "billing",
        annotate=QUESTIONS[0],
        annotate_provider=DecisionsConfig.custom(
            "decisions-mine", {"maxDocuments": 50, "model": "m"}
        ),
    )
    sent = service.captured_request.annotate.provider
    assert sent.WhichOneof("kind") == "custom"
    assert sent.custom.module == "decisions-mine"
    assert dict(sent.custom.settings) == {"maxDocuments": 50, "model": "m"}

    collection.query.bm25(
        "billing", annotate=QUESTIONS[0], annotate_provider=DecisionsConfig.custom("decisions-mine")
    )
    sent = service.captured_request.annotate.provider
    assert sent.custom.module == "decisions-mine"
    assert not sent.custom.HasField("settings")

    collection.query.bm25("billing", annotate=QUESTIONS[0])
    assert not service.captured_request.annotate.HasField("provider")


def test_rerank_provider_is_sent(
    decisions_collection: tuple[weaviate.collections.Collection, MockDecisionsWeaviateService],
) -> None:
    collection, service = decisions_collection

    collection.query.bm25(
        "billing",
        rerank=Rerank.decide(
            prop="text", query="angry", provider=DecisionsConfig.openai(max_documents=20)
        ),
    )
    sent = service.captured_request.rerank
    assert sent.HasField("decision")
    assert sent.provider.decisions.WhichOneof("kind") == "openai"
    assert sent.provider.decisions.openai.max_documents == 20

    collection.query.bm25("billing", rerank=Rerank.decide(prop="text", query="angry"))
    assert not service.captured_request.rerank.HasField("provider")


def test_rerank_and_annotate_take_different_providers(
    decisions_collection: tuple[weaviate.collections.Collection, MockDecisionsWeaviateService],
) -> None:
    collection, service = decisions_collection

    collection.query.bm25(
        "billing",
        rerank=Rerank.decide(prop="text", query="angry", provider=DecisionsConfig.openai()),
        annotate=QUESTIONS[0],
        annotate_provider=DecisionsConfig.typesafeai(),
    )
    request = service.captured_request
    assert request.rerank.provider.decisions.WhichOneof("kind") == "openai"
    assert request.annotate.provider.WhichOneof("kind") == "typesafeai"


def test_annotate_provider_needs_annotate(
    decisions_collection: tuple[weaviate.collections.Collection, MockDecisionsWeaviateService],
) -> None:
    collection, service = decisions_collection
    service.captured_request = search_get_pb2.SearchRequest()

    with pytest.raises(WeaviateInvalidInputError, match="annotate_provider"):
        collection.query.bm25("billing", annotate_provider=DecisionsConfig.openai())
    assert service.captured_request.collection == "", "nothing was sent"


@pytest.mark.parametrize("name", ["", "  "])
def test_a_custom_provider_needs_a_module_name(name: str) -> None:
    with pytest.raises(WeaviateInvalidInputError):
        DecisionsConfig.custom(name)


def test_a_provider_max_documents_is_positive() -> None:
    with pytest.raises(ValidationError):
        DecisionsConfig.openai(max_documents=0)
