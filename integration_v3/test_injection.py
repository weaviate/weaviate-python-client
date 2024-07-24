import pytest
import weaviate
import requests
import json


def injection_template(n: int) -> str:
    return "Liver" + ("\\" * n) + '"}}){{answer}}}}{payload}#'


@pytest.mark.parametrize("n_backslashes", [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
def test_gql_injection(n_backslashes: int) -> None:
    client = weaviate.Client(url="http://localhost:8080")
    client.schema.delete_class("Question")
    client.schema.delete_class("Hacked")
    class_obj = {
        "class": "Question",
        "vectorizer": "text2vec-contextionary",
        "properties": [
            {"name": "answer", "dataType": ["string"], "tokenization": "field"},
            {"name": "question", "dataType": ["string"]},
            {"name": "category", "dataType": ["string"]},
        ],
    }

    class_obj2 = {
        "class": "Hacked",
        "vectorizer": "text2vec-contextionary",
        "properties": [
            {"name": "answer", "dataType": ["string"]},
            {"name": "question", "dataType": ["string"]},
            {"name": "category", "dataType": ["string"]},
        ],
    }
    client.schema.create_class(class_obj)
    client.schema.create_class(class_obj2)

    resp = requests.get(
        "https://raw.githubusercontent.com/weaviate-tutorials/quickstart/main/data/jeopardy_tiny.json"
    )
    data = json.loads(resp.text)

    client.batch.configure(batch_size=100)
    with client.batch as batch:
        for _, d in enumerate(data):
            properties = {
                "answer": d["Answer"],
                "question": d["Question"],
                "category": d["Category"],
            }
            batch.add_data_object(data_object=properties, class_name="Question")
            batch.add_data_object(data_object=properties, class_name="Hacked")

    injection_payload = client.query.get("Hacked", ["answer"]).build()
    query = client.query.get("Question", ["question", "answer", "category"]).with_where(
        {
            "path": ["answer"],
            "operator": "NotEqual",
            "valueText": injection_template(n_backslashes).format(payload=injection_payload[1:]),
        }
    )
    res = query.do()
    assert "Hacked" not in res["data"]["Get"]
