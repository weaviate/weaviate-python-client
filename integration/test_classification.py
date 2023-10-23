import pytest

import weaviate

schema = {
    "classes": [
        {
            "class": "Label",
            "description": "a label describing a message",
            "properties": [
                {
                    "name": "name",
                    "description": "The name of this label",
                    "dataType": ["string"],
                },
                {
                    "name": "description",
                    "description": "The description of this label",
                    "dataType": ["text"],
                },
            ],
        },
        {
            "class": "Message",
            "description": "a message from written by a person",
            "properties": [
                {
                    "name": "content",
                    "description": "The content of the message",
                    "dataType": ["text"],
                },
                {
                    "name": "labeled",
                    "description": "The label assigned to this message",
                    "dataType": ["Label"],
                },
            ],
        },
    ]
}


@pytest.fixture(scope="module")
def client():
    client = weaviate.Client("http://localhost:8080")
    client.schema.create(schema)
    yield client
    client.schema.delete_all()


def test_contextual(client: weaviate.Client):
    # Create labels
    client.data_object.create(
        {"name": "positive", "description": "A positive, good, happy or supporting message."},
        "Label",
    )
    client.data_object.create(
        {"name": "negative", "description": "A negative, bad, sad or disrupting message."}, "Label"
    )

    client.data_object.create(
        {
            "content": "ALERT: So now we find out that the entire opponent “hit squad” illegally wiped their phones clean just prior to the investigation of them, all using the same really dumb reason for this “accident”, just like other people smashing her phones with a hammer, & DELETING THEIR EMAILS!"
        },
        "Message",
    )
    client.data_object.create(
        {
            "content": "I'm so happy, proud and excited to be a part of this community for the rest of my days."
        },
        "Message",
    )
    client.data_object.create(
        {"content": "thank you for reminding the world of our cause"}, "Message"
    )

    client.classification.schedule().with_type("text2vec-contextionary-contextual").with_class_name(
        "Message"
    ).with_based_on_properties(["content"]).with_classify_properties(
        ["labeled"]
    ).with_wait_for_completion().do()

    result = (
        client.query.get("Message", ["content", "labeled {... on Label {name description}}"])
        .with_additional(["id", "classification{basedOn, id}"])
        .do()
    )
    labeled_messages = result["data"]["Get"]["Message"]
    for message in labeled_messages:
        assert message["labeled"] is not None
        assert message["_additional"]["id"] is not None
