import unittest
from weaviate.gql.get import GetBuilder


class TestGetBuilder(unittest.TestCase):

    def test___init__(self):
        """
        Test the `__init__` method.
        """

        class_name_error_message = f"class name must be of type str but was {int}"
        properties_error_message = ("properties must be of type str or "
                f"list of str but was {int}")

        # invalid calls
        with self.assertRaises(TypeError) as error:
            GetBuilder(1, ["a"], None)
        self.assertEqual(str(error.exception), class_name_error_message)

        with self.assertRaises(TypeError) as error:
            GetBuilder("A", 2, None)
        self.assertEqual(str(error.exception), properties_error_message)

        # valid calls
        GetBuilder("name", "prop", None)
        GetBuilder("name", ["prop1", "prop2"], None)

    def test_build_with_limit(self):
        """
        Test the `with_limit` method.
        """

        # valid calls
        query = GetBuilder("Person", "name", None).with_limit(20).build()
        self.assertEqual('{Get{Person(limit: 20 ){name}}}', query)

        # invalid calls
        limit_error_message = 'limit cannot be non-positive (limit >=1).'
        with self.assertRaises(ValueError) as error:
            GetBuilder("A", ["str"], None).with_limit(0)
        self.assertEqual(str(error.exception), limit_error_message)

        with self.assertRaises(ValueError) as error:
            GetBuilder("A", ["str"], None).with_limit(-1)
        self.assertEqual(str(error.exception), limit_error_message)


    def test_build_with_where(self):
        """
        Thest the ` with_where` method.
        """

        filter = {
            "path": ["name"],
            "operator": "Equal",
            "valueString": "A"
        }
        query = GetBuilder("Person", "name", None).with_where(filter).build()
        self.assertEqual('{Get{Person(where: {path: ["name"] operator: Equal valueString: "A"} ){name}}}', query)

    def test_build_with_near_text(self):
        """
        Test the `with_near_text` method.
        """

        near_text = {
            "concepts": "computer",
            "moveTo": {
                "concepts": ["science"],
                "force": 0.5
            },
        }

        # valid calls
        query = GetBuilder("Person", "name", None).with_near_text(near_text).build()
        self.assertEqual('{Get{Person(nearText: {concepts: ["computer"] moveTo: {concepts: ["science"] force: 0.5}} ){name}}}', query)

        # invalid calls
        near_error_message = "Cannot use both 'nearText' and 'nearVector' filters!"
        with self.assertRaises(AttributeError) as error:
            GetBuilder("Person", "name", None).with_near_text(near_text).with_near_vector(near_text)
        self.assertEqual(str(error.exception), near_error_message)

    def test_build_near_vector(self):
        """
        Test the `with_near_vector` method.
        """

        near_vector = {
            "vector": [1, 2, 3, 4, 5, 6, 7, 8, 9],
            "certainty": 0.55
        }

        # valid calls
        query = GetBuilder("Person", "name", None).with_near_vector(near_vector).build()
        self.assertEqual('{Get{Person(nearVector: {vector: [1, 2, 3, 4, 5, 6, 7, 8, 9] certainty: 0.55} ){name}}}', query)

        # invalid calls
        near_error_message = "Cannot use both 'nearText' and 'nearVector' filters!"
        with self.assertRaises(AttributeError) as error:
            GetBuilder("Person", "name", None).with_near_vector(near_vector).with_near_text(near_vector)
        self.assertEqual(str(error.exception), near_error_message)

    def test_build(self):
        """
        Test the `build` method. (without filters)
        """

        query = GetBuilder("Group", "name", None).build()
        self.assertEqual("{Get{Group{name}}}", query)

        query = GetBuilder("Group", ["name", "uuid"], None).build()
        self.assertEqual("{Get{Group{name uuid}}}", query)

        query = GetBuilder("Group", ["name", "uuid"], None).build()
        self.assertEqual("{Get{Group{name uuid}}}", query)
        
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
