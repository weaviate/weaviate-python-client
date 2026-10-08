import pytest

import weaviate
from mock_tests.conftest import MockDecisionsWeaviateService
from weaviate.classes.query import Decide
from weaviate.collections.classes.internal import DecisionAnswer
from weaviate.exceptions import WeaviateInvalidInputError

QUESTIONS = [
    Decide.predicate("angry", prop="text", instructions="Is the customer angry?"),
    Decide.choice(
        "team",
        prop="text",
        instructions="Which team should handle this?",
        options={"billing": "money and invoices", "support": None},
    ),
    Decide.score(
        "severity",
        prop="text",
        instructions="How severe is the complaint?",
        levels=["low", "medium", "high"],
    ),
    Decide.predicate("refused", prop="text", instructions="refuse"),
]


def test_decide_is_sent_and_answers_are_parsed(
    decisions_collection: tuple[weaviate.collections.Collection, MockDecisionsWeaviateService],
) -> None:
    collection, service = decisions_collection

    objs = collection.query.bm25("billing", decide=QUESTIONS).objects

    sent = service.captured_request.decide.questions
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
    assert objs[0].decisions == {
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
    assert objs[1].decisions is None, "an object without decisions has none"


def test_a_single_question_is_accepted(
    decisions_collection: tuple[weaviate.collections.Collection, MockDecisionsWeaviateService],
) -> None:
    collection, service = decisions_collection

    collection.query.bm25("billing", decide=QUESTIONS[0])

    assert [q.name for q in service.captured_request.decide.questions] == ["angry"]


def test_no_decide_sends_no_questions(
    decisions_collection: tuple[weaviate.collections.Collection, MockDecisionsWeaviateService],
) -> None:
    collection, service = decisions_collection

    objs = collection.query.bm25("billing").objects

    assert not service.captured_request.HasField("decide")
    assert objs[0].decisions is not None, "the mock answers regardless of the request"


@pytest.mark.parametrize(
    "build",
    [
        lambda: Decide.choice("t", prop="p", instructions="i", options={"only": None}),
        lambda: Decide.choice("t", prop="p", instructions="i", options="ab"),  # type: ignore[arg-type]
        lambda: Decide.score("t", prop="p", instructions="i", levels=["only"]),
        lambda: Decide.score("t", prop="p", instructions="i", levels="ab"),  # type: ignore[arg-type]
    ],
)
def test_questions_need_at_least_two_named_answers(build) -> None:
    with pytest.raises(WeaviateInvalidInputError):
        build()
