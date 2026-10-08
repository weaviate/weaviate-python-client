import os

import pytest

import weaviate.classes as wvc
from weaviate.collections.classes.config import Decisions, DecisionsQuestion

from .conftest import CollectionFactory


def test_decisions_openai(collection_factory: CollectionFactory) -> None:
    api_key = os.environ.get("OPENAI_APIKEY")
    if api_key is None:
        pytest.skip("No OpenAI API key found.")

    collection = collection_factory(
        decisions_config=wvc.config.Configure.Decisions.openai(
            question=DecisionsQuestion.STATEMENT, max_documents=10
        ),
        vectorizer_config=wvc.config.Configure.Vectorizer.none(),
        properties=[wvc.config.Property(name="text", data_type=wvc.config.DataType.TEXT)],
        headers={"X-OpenAI-Api-Key": api_key},
    )
    if "decisions-openai" not in collection._connection.get_meta()["modules"]:
        pytest.skip("the server has no decisions-openai module")

    config = collection.config.get()
    assert config.decisions_config is not None
    assert config.decisions_config.decisions == Decisions.OPENAI
    assert config.decisions_config.model["question"] == "statement"
    assert config.decisions_config.model["maxDocuments"] == 10

    collection.data.insert_many(
        [
            {
                "text": "I still have not received my refund after three weeks and nobody answers my emails. This is unacceptable."
            },
            {"text": "Thanks a lot, the replacement arrived today and works perfectly."},
        ]
    )

    objs = collection.query.bm25(
        "refund arrived",
        rerank=wvc.query.Rerank(prop="text", query="The customer is unhappy"),
        decide=[
            wvc.query.Decide.predicate("angry", prop="text", instructions="Is the customer angry?"),
            wvc.query.Decide.choice(
                "team",
                prop="text",
                instructions="Which team should handle this message?",
                options={"billing": "refunds, invoices and payments", "none": "no action needed"},
            ),
            wvc.query.Decide.score(
                "urgency",
                prop="text",
                instructions="How urgent is this message?",
                levels=["low", "medium", "high"],
            ),
        ],
    ).objects

    assert len(objs) == 2
    unhappy, happy = objs[0], objs[1]
    assert "refund" in str(unhappy.properties["text"])
    assert unhappy.metadata.rerank_score is not None and happy.metadata.rerank_score is not None
    assert unhappy.metadata.rerank_score > happy.metadata.rerank_score

    for obj in objs:
        assert obj.decisions is not None
        assert set(obj.decisions) == {"angry", "team", "urgency"}
        assert obj.decisions["team"].probabilities is not None
        assert set(obj.decisions["team"].probabilities) == {"billing", "none"}
        assert obj.decisions["urgency"].probabilities is not None
        assert set(obj.decisions["urgency"].probabilities) == {"low", "medium", "high"}
    assert unhappy.decisions is not None and happy.decisions is not None
    assert unhappy.decisions["angry"].probability is not None
    assert happy.decisions["angry"].probability is not None
    assert unhappy.decisions["angry"].probability > happy.decisions["angry"].probability
    assert unhappy.decisions["team"].choice == "billing"
    assert happy.decisions["team"].choice == "none"
    assert unhappy.decisions["urgency"].score is not None
    assert happy.decisions["urgency"].score is not None
    assert unhappy.decisions["urgency"].score > happy.decisions["urgency"].score
