import unittest
from weaviate.gql.aggregate import AggregateBuilder


class TestAggregateBuilder(unittest.TestCase):

    def test_with_meta(self):
        query = AggregateBuilder("Object", None, "Things")\
            .with_meta_count()\
            .build()
        self.assertEqual("{Aggregate{Things{Object{meta{count}}}}}", query)

    def test_with_field(self):
        query = AggregateBuilder("Object", None, "Things") \
            .with_fields("size { mean }") \
            .build()
        self.assertEqual("{Aggregate{Things{Object{size { mean }}}}}", query)

    def test_with_where_filter(self):
        filter = {
            "operator": "Equal",
            "valueString": "B",
            "path": ["name"]
        }

        query = AggregateBuilder("Object", None, "Things")\
            .with_meta_count()\
            .with_where(filter)\
            .build()
        self.assertEqual('{Aggregate{Things{Object(where: {path: ["name"] operator: Equal valueString: "B"} ){meta{count}}}}}', query)

    def test_group_by(self):
        query = AggregateBuilder("Object", None, "Things")\
            .with_group_by_filter(["name"])\
            .with_fields("groupedBy { value }")\
            .with_fields("name { count }")\
            .build()
        self.assertEqual('{Aggregate{Things{Object(groupBy: ["name"]){groupedBy { value }name { count }}}}}', query)

    def test_group_by_and_where(self):
        filter = {
          "path": ["name"],
          "operator": "Equal",
          "valueString": "B"
        }

        query = AggregateBuilder("Object", None, "Things") \
            .with_group_by_filter(["name"]) \
            .with_fields("groupedBy { value }") \
            .with_fields("name { count }") \
            .with_where(filter)\
            .build()
        self.assertEqual('{Aggregate{Things{Object(where: {path: ["name"] operator: Equal valueString: "B"} groupBy: ["name"]){groupedBy { value }name { count }}}}}', query)

