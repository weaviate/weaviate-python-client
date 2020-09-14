import weaviate
import time


class TestFailedException(Exception):
    def __init__(self, message):
        super().__init__(message)


schema = {
    "things": {
        "classes": [
            {
                "class": "Ship",
                "description": "object",
                "properties": [
                    {
                        "dataType": [
                            "string"
                        ],
                        "description": "name",
                        "name": "name"
                    },
                    {
                        "dataType": [
                            "int"
                        ],
                        "description": "size",
                        "name": "size"
                    }
                ]
            },
        ],
        "type": "thing"
    }
}


class TestGraphQL:

    def __init__(self, client:weaviate.Client):
        self.client = client
        self.client.schema.create(schema)

        client.data_object.create({"name": "A", "size": 5}, "Ship")
        client.data_object.create({"name": "B", "size": 20}, "Ship")
        client.data_object.create({"name": "C", "size": 43}, "Ship")
        client.data_object.create({"name": "D", "size": 1}, "Ship")
        client.data_object.create({"name": "E", "size": 34}, "Ship")
        client.data_object.create({"name": "F", "size": 303}, "Ship")
        time.sleep(2.0)

    def query_data(self):
        where_filter = {
            "path": ["size"],
            "operator":  "LessThan",
            "valueInt": 10
        }
        result = self.client.query.get\
            .things("Ship", ["name", "size"])\
            .with_limit(2)\
            .with_where(where_filter)\
            .do()
        objects = get_objects_from_result(result)
        a_found = False
        d_found = False
        for obj in objects:
            if obj["name"] == "A":
                a_found = True
            if obj["name"] == "D":
                d_found = True
        if a_found and d_found and len(objects) == 2:
            return
        raise TestFailedException("GraphQL result not right")

    def aggregate_data(self):
        filter = {
            "path": ["name"],
            "operator": "Equal",
            "valueString": "B"
        }

        result = self.client.query.aggregate \
            .things("Ship") \
            .with_where(filter) \
            .with_group_by_filter(["name"]) \
            .with_fields("groupedBy {value}") \
            .with_fields("name{count}") \
            .do()

        aggregation = get_aggregation_from_aggregate_result(result)
        if "groupedBy" not in aggregation:
            raise TestFailedException("Missing groupedBy")
        if "name" not in aggregation:
            raise TestFailedException("Missing name property")


def get_objects_from_result(result):
    return result["data"]["Get"]["Things"]["Ship"]


def get_aggregation_from_aggregate_result(result):
    return result["data"]["Aggregate"]["Things"]["Ship"][0]


if __name__ == "__main__":
    client = weaviate.Client("http://localhost:8080")
    gql = TestGraphQL(client)
    gql.query_data()
    gql.aggregate_data()
