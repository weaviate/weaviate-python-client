import unittest
from weaviate.gql.filter import NearText, NearVector, WhereFilter


def helper_get_test_filter(type, value):
    return {
        "path": ["name"],
        "operator": "Equal",
        type: value
    }


class TestNearText(unittest.TestCase):

    def move_x_test_case(self, move: str):
        """
        Test the "moveTo" or the "moveAwayFrom" clause.

        Parameters
        ----------
        move : str
            The "moveTo" or the "moveAwayFrom" clause name.
        """

        with self.assertRaises(TypeError):
            NearText({
                "concepts": "Some_concept",
                move: "0.5"
            })
        with self.assertRaises(ValueError):
            NearText({
                "concepts": "Some_concept",
                move: {"Invalid" : "something"}
            })
        with self.assertRaises(TypeError):
            NearText({
                "concepts": "Some_concept",
                move: {
                    "concepts" : set("something")
                }
            })
        with self.assertRaises(ValueError):
            NearText({
                "concepts": "Some_concept",
                move: {
                    "concepts" : "something",
                }
            })
        with self.assertRaises(TypeError):
            NearText({
                "concepts": "Some_concept",
                move: {
                    "concepts": "something",
                    "force": True
                }
            })

    def test___init__(self):
        """
        Test the `__init__` method.
        """

        # test exceptions
        # test "concepts"
        with self.assertRaises(TypeError):
            NearText(["concepts", "Some_concept"])
        with self.assertRaises(ValueError):
            NearText({"INVALID": "Some_concept"})
        with self.assertRaises(TypeError):
            NearText({"concepts" : set("Some_concept")})
        # test "certainty"
        with self.assertRaises(TypeError):
            NearText({
                "concepts": "Some_concept",
                "certainty": "0.5"
            })
        # test "moveTo"
        self.move_x_test_case("moveTo")
        # test "moveAwayFrom"
        self.move_x_test_case("moveAwayFrom")

        # test valid calls
        self.assertIsInstance(NearText(
            {
                "concepts": "Some_concept"
            }),
            NearText
        )
        self.assertIsInstance(NearText(
            {
                "concepts": ["Some_concept", "Some_concept_2"]
            }),
            NearText
        )
        self.assertIsInstance(NearText(
            {
                "concepts": "Some_concept",
                "certainty": 0.75
            }),
            NearText
        )
        self.assertIsInstance(NearText(
            {
                "concepts": "Some_concept",
                "moveTo": {
                    "concepts": "moveToConcepts",
                    "force": 0.75
                }
            }),
            NearText
        )
        self.assertIsInstance(NearText(
            {
                "concepts": "Some_concept",
                "moveAwayFrom": {
                    "concepts": "moveAwayFromConcepts",
                    "force": 0.75
                }
            }),
            NearText
        )
        self.assertIsInstance(NearText(
            {
                "concepts": "Some_concept",
                "certainty": 0.75,
                "moveAwayFrom": {
                    "concepts": "moveAwayFromConcepts",
                    "force": 0.75
                },
                "moveTo": {
                    "concepts": "moveToConcepts",
                    "force": 0.75
                }
            }),
            NearText
        )

    def test___str__(self):
        """
        Test the `__str__` method.
        """
        
        near_text = NearText(
            {
                "concepts": "Some_concept"
            }
        )
        self.assertEqual(str(near_text), 'nearText: {concepts: ["Some_concept"]} ')

        near_text = NearText(
            {
                "concepts": ["Some_concept", "Some_concept_2"]
            }
        )
        self.assertEqual(str(near_text), 'nearText: {concepts: ["Some_concept", "Some_concept_2"]} ')
        near_text = NearText(
            {
                "concepts": "Some_concept",
                "certainty": 0.75
            }
        )
        self.assertEqual(str(near_text), 'nearText: {concepts: ["Some_concept"] certainty: 0.75} ')
        near_text = NearText(
            {
                "concepts": "Some_concept",
                "moveTo": {
                    "concepts": "moveToConcepts",
                    "force": 0.75
                }
            }
        )
        self.assertEqual(str(near_text), 'nearText: {concepts: ["Some_concept"] moveTo: {concepts: ["moveToConcepts"] force: 0.75}} ')
        near_text = NearText(
            {
                "concepts": "Some_concept",
                "moveAwayFrom": {
                    "concepts": "moveAwayFromConcepts",
                    "force": 0.25
                }
            }
        )
        self.assertEqual(str(near_text), 'nearText: {concepts: ["Some_concept"] moveAwayFrom: {concepts: ["moveAwayFromConcepts"] force: 0.25}} ')
        near_text = NearText(
            {
                "concepts": "Some_concept",
                "certainty": 0.95,
                "moveAwayFrom": {
                    "concepts": "moveAwayFromConcepts",
                    "force": 0.75
                },
                "moveTo": {
                    "concepts": "moveToConcepts",
                    "force": 0.25
                }
            }
        )
        self.assertEqual(str(near_text), 'nearText: {concepts: ["Some_concept"] certainty: 0.95 moveTo: {concepts: ["moveToConcepts"] force: 0.25} moveAwayFrom: {concepts: ["moveAwayFromConcepts"] force: 0.75}} ')

        # test it with references of objects
        concepts = ["con1", "con2"]
        move = {
            "concepts": "moveToConcepts",
            "force": 0.75
        }

        near_text = NearText(
            {
                "concepts": concepts,
                "moveTo": move
            }
        )
        concepts.append("con3") # should not be appended to the nearText clause
        move["force"] = 2.00 # should not be appended to the nearText clause
        self.assertEqual(str(near_text), 'nearText: {concepts: ["con1", "con2"] moveTo: {concepts: ["moveToConcepts"] force: 0.75}} ')

class TestNearVector(unittest.TestCase):

    def test___init__(self):
        """
        Test the `__init__` method.
        """

        # test exceptions
        # test "concepts"
        with self.assertRaises(TypeError):
            NearVector(["concepts", "Some_concept"])
        with self.assertRaises(ValueError):
            NearVector({"INVALID": "Some_concept"})
        with self.assertRaises(TypeError):
            NearVector({"vector" : set("Some_concept")})
        # test "certainty"
        with self.assertRaises(TypeError):
            NearVector({
                "vector": [1., 2., 3., 4.],
                "certainty": "0.5"
            })

        # test valid calls
        self.assertIsInstance(NearVector(
            {
                "vector": [1., 2., 3., 4.]
            }),
            NearVector
        )
        self.assertIsInstance(NearVector(
            {
                "vector": [1., 2., 3., 4.],
                "certainty": 0.75
            }),
            NearVector
        )

    def test___str__(self):
        """
        Test the `__str__` method.
        """
        
        near_vector = NearVector(
            {
                "vector": [1., 2., 3., 4.]
            }
        )
        self.assertEqual(str(near_vector), 'nearVector: {vector: [1.0, 2.0, 3.0, 4.0]} ')
        near_vector = NearVector(
            {
                "vector": [1., 2., 3., 4.],
                "certainty": 0.75
            }
        )
        self.assertEqual(str(near_vector), 'nearVector: {vector: [1.0, 2.0, 3.0, 4.0] certainty: 0.75} ')

class TestWhereFilter(unittest.TestCase):

    def test___init__(self):
        """
        Test the `__init__` method.
        """

        # test exceptions
        with self.assertRaises(TypeError):
            WhereFilter(None)
        with self.assertRaises(TypeError):
            WhereFilter("filter")
        with self.assertRaises(ValueError):
            WhereFilter({})
        with self.assertRaises(ValueError):
            WhereFilter({"path": "some_path"})
        with self.assertRaises(ValueError):
            WhereFilter({"path": "some_path", "operator": "Like"})
        with self.assertRaises(ValueError):
            WhereFilter({"operands": "some_path"})
        with self.assertRaises(TypeError):
            WhereFilter({"operands": "some_path", "operator": "Like"})
        with self.assertRaises(TypeError):
            WhereFilter({"operands": ["some_path"], "operator": "Like"})
        
        # test valid calls
        self.assertIsInstance(
            WhereFilter(
                {
                    "path": "hasTheOneRing",
                    "operator" : "Equal",
                    "valueBoolean" : False
                }
            ),
            WhereFilter
        )
        self.assertIsInstance(
            WhereFilter(
                {
                    "operands": [{
                        "path": "hasTheOneRing",
                        "operator" : "Equal",
                        "valueBoolean" : False
                    },
                    {
                        "path": "hasFriend",
                        "operator" : "Equal",
                        "valueText" : "Samwise Gamgee"
                    }],
                    "operator" : "And"
                }
            ),
            WhereFilter
        )

    def test___str__(self):
        """
        Test the `__str__` method.
        """

        test_filter = {
            "path": ["name"],
            "operator": "Equal",
            "valueString": "A"
        }
        result = str(WhereFilter(test_filter))
        self.assertEqual('where: {path: ["name"] operator: Equal valueString: "A"} ', result)

        test_filter = {
            "operator": "Or",
            "operands": [{
                "path": ["name"],
                "operator": "Equal",
                "valueString": "Alan Truing"
            },
                {
                    "path": ["name"],
                    "operator": "Equal",
                    "valueString": "John von Neumann"
                }
            ]
        }
        result = str(WhereFilter(test_filter))
        self.assertEqual(
            'where: {operator: Or operands: [{path: ["name"] operator: Equal valueString: "Alan Truing"}, {path: ["name"] operator: Equal valueString: "John von Neumann"}]} ',
            result
        )

        test_filter = helper_get_test_filter("valueInt", 1)
        result = str(WhereFilter(test_filter))
        self.assertEqual('where: {path: ["name"] operator: Equal valueInt: 1} ', result)

        test_filter = helper_get_test_filter("valueNumber", 1.4)
        result = str(WhereFilter(test_filter))
        self.assertEqual('where: {path: ["name"] operator: Equal valueNumber: 1.4} ', result)

        test_filter = helper_get_test_filter("valueBoolean", True)
        result = str(WhereFilter(test_filter))
        self.assertEqual('where: {path: ["name"] operator: Equal valueBoolean: true} ', result)

        geo_range = {
            "geoCoordinates": {
                "latitude": 51.51,
                "longitude": -0.09
            },
            "distance": {
                "max": 2000
            }
        }
        test_filter = helper_get_test_filter("valueGeoRange", geo_range)
        result = str(WhereFilter(test_filter))
        self.assertEqual('where: {path: ["name"] operator: Equal valueGeoRange: {"geoCoordinates": {"latitude": 51.51, "longitude": -0.09}, "distance": {"max": 2000}}} ', str(result))
