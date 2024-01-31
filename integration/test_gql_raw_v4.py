import weaviate
from weaviate.client import WeaviateClient
from weaviate.collections.classes.config import DataType, Property, Configure


def test_raw_gql_v4() -> None:
    name = "RawGraphQlTest"
    number = 20
    client: WeaviateClient = weaviate.connect_to_local()
    client.collections.delete(name)
    collection = client.collections.create(
        name=name,
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    collection.data.insert_many([{"Name": f"name {i}"} for i in range(number)])

    response = client.graphql_raw_query(
        """{
                                        Aggregate {RawGraphQlTest{meta {count}}}
                                        Get{RawGraphQlTest{name}}
                                        }"""
    )

    assert response.errors is None
    assert response.aggregate[name][0]["meta"]["count"] == number
    assert len(response.get[name]) == number


def test_raw_gql_v4_error() -> None:
    client: WeaviateClient = weaviate.connect_to_local()

    response = client.graphql_raw_query(
        """{
                                        Get{IDoNotExist{name}}
                                        }"""
    )

    assert response.errors is not None
    assert len(response.get) == 0
    assert len(response.aggregate) == 0
    assert len(response.explore) == 0
