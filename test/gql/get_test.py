import unittest
from weaviate.gql.get import GetBuilder


class TestGetBuilder(unittest.TestCase):

    def test___init__(self):
        """
        Test the `__init__` method.
        """

        # test exceptions
        with self.assertRaises(TypeError):
            GetBuilder(1, ["a"], None)
        with self.assertRaises(TypeError):
            GetBuilder("A", 2, None)

        # test valid calls
        self.assertIsInstance(GetBuilder("name", "prop", None), GetBuilder)
        self.assertIsInstance(GetBuilder("name", ["prop1", "prop2"], None), GetBuilder)



    def test_build_simple_query(self):
        query = GetBuilder("Group", "name", None).build()
        self.assertEqual("{Get{Group{name}}}", query)

        query = GetBuilder("Group", ["name", "uuid"], None).build()
        self.assertEqual("{Get{Group{name uuid}}}", query)

        query = GetBuilder("Group", ["name", "uuid"], None).build()
        self.assertEqual("{Get{Group{name uuid}}}", query)

    def test_build_limited_query(self):
        query = GetBuilder("Person", "name", None).with_limit(20).build()
        self.assertEqual('{Get{Person(limit: 20 ){name}}}', query)

    def test_build_where_limited_query(self):
        filter = {
            "path": ["name"],
            "operator": "Equal",
            "valueString": "A"
        }
        query = GetBuilder("Person", "name", None).with_limit(1).with_where(filter).build()
        self.assertEqual('{Get{Person(where: {path: ["name"] operator: Equal valueString: "A"} limit: 1 ){name}}}', query)

    def test_build_near_text(self):
        near_text = {
            "concepts": "computer",
            "moveTo": {
                "concepts": ["science"],
                "force": 0.5
            },
        }
        query = GetBuilder("Person", "name", None).with_near_text(near_text).build()
        self.assertEqual('{Get{Person(nearText: {concepts: ["computer"] moveTo: {concepts: ["science"] force: 0.5}} ){name}}}', query)

        with self.assertRaises(AttributeError):
            GetBuilder("Person", "name", None).with_near_text(near_text).with_near_vector(near_text)

    def test_build_near_vector(self):
        near_vector = {
            "vector": [1, 2, 3, 4, 5, 6, 7, 8, 9],
            "certainty": 0.55
        }
        query = GetBuilder("Person", "name", None).with_near_vector(near_vector).build()
        self.assertEqual('{Get{Person(nearVector: {vector: [1, 2, 3, 4, 5, 6, 7, 8, 9] certainty: 0.55} ){name}}}', query)

        with self.assertRaises(AttributeError):
            GetBuilder("Person", "name", None).with_near_vector(near_vector).with_near_text(near_vector)

    def test_build_full_query(self):
        near_text = {
            "concepts": ["computer"],
            "moveTo": {
                "concepts": "science",
                "force": 0.1
            },
            "moveAwayFrom": {
                "concepts": ["airplane"],
                "force": 0.2
            },
            "certainty": 0.3
        }
        filter = {
            "operator": "Or",
            "operands": [{
                "path": ["name"],
                "operator": "Equal",
                "valueString": "Alan Turing",
            }, {
                "path": ["name"],
                "operator": "Equal",
                "valueString": "John von Neumann"
            }]
        }
        query = GetBuilder("Person", ["name", "uuid"], None)\
            .with_near_text(near_text)\
            .with_where(filter)\
            .with_limit(2)\
            .build()
        self.assertEqual('{Get{Person(where: {operator: Or operands: [{path: ["name"] operator: Equal valueString: "Alan Turing"}, {path: ["name"] operator: Equal valueString: "John von Neumann"}]} limit: 2 nearText: {concepts: ["computer"] certainty: 0.3 moveTo: {concepts: ["science"] force: 0.1} moveAwayFrom: {concepts: ["airplane"] force: 0.2}} ){name uuid}}}', query)
