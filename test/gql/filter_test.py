import unittest
from weaviate.gql.filter import *


def helper_get_test_filter(type, value):
    return {
        "path": ["name"],
        "operator": "Equal",
        type: value
    }


class TestGraphQLFilter(unittest.TestCase):

    def _expect_filter_error(self, filter, expected_error):
        try:
            WhereFilter(filter)
            self.fail()
        except expected_error:
            pass

    def test_filter_inputs(self):
        self._expect_filter_error("", TypeError)
        test_filter = {
            "path": ["name"],
            "operator": "Equal",
        }
        self._expect_filter_error(test_filter, ValueError)
        test_filter = {
            "path": ["name"],
            "valueString": "John von Neumann"
        }
        self._expect_filter_error(test_filter, ValueError)
        test_filter = {
            "operator": "Equal",
            "valueString": "John von Neumann"
        }
        self._expect_filter_error(test_filter, ValueError)
        test_filter = {
            "operands": []
        }
        self._expect_filter_error(test_filter, ValueError)

    def test_filter_generation(self):
        test_filter = {
            "path": ["name"],
            "operator": "Equal",
            "valueString": "A"
        }
        f = WhereFilter(test_filter)
        result = str(f).replace(" ", "")  # Remove all the spaces
        self.assertEqual('{path:["name"]operator:EqualvalueString:"A"}', result)

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
        f = WhereFilter(test_filter)
        self.assertEqual(
            '{operator: Or operands: [{path: ["name"] operator: Equal valueString: "Alan Truing"}, {path: ["name"] operator: Equal valueString: "John von Neumann"}]}',
            str(f))

    def test_filter_generation_none_str_types(self):
        test_filter = helper_get_test_filter("valueInt", 1)
        f = WhereFilter(test_filter)
        self.assertEqual('{path: ["name"] operator: Equal valueInt: 1}', str(f))

        test_filter = helper_get_test_filter("valueNumber", 1.4)
        f = WhereFilter(test_filter)
        self.assertEqual('{path: ["name"] operator: Equal valueNumber: 1.4}', str(f))

        test_filter = helper_get_test_filter("valueBoolean", True)
        f = WhereFilter(test_filter)
        self.assertEqual('{path: ["name"] operator: Equal valueBoolean: true}', str(f))

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
        f = WhereFilter(test_filter)
        self.assertEqual('{path: ["name"] operator: Equal valueGeoRange: {"geoCoordinates": {"latitude": 51.51, "longitude": -0.09}, "distance": {"max": 2000}}}', str(f))

    def test_explore_filter_inputs(self):
        try:
            Explore("x")
            self.fail("expected error")
        except TypeError:
            pass
        try:
            Explore({})
            self.fail("expected error")
        except ValueError:
            pass
        try:
            Explore({"concepts": 1})
            self.fail("expected error")
        except ValueError:
            pass
        try:
            Explore({"concepts": "c", "certainty": "x"})
            self.fail("expected error")
        except TypeError:
            pass
        try:
            Explore({"concepts": "c", "moveTo": "x"})
            self.fail("expected error")
        except TypeError:
            pass
        try:
            Explore({"concepts": "c", "moveAwayFrom": "x"})
            self.fail("expected error")
        except TypeError:
            pass
        try:
            Explore({"concepts": "c", "moveTo": {}})
            self.fail("expected error")
        except ValueError:
            pass
        try:
            Explore({"concepts": "c", "moveTo": {"concepts": "a"}})
            self.fail("expected error")
        except ValueError:
            pass
        try:
            Explore({"concepts": "c", "moveTo": {"concepts": "a", "force": "a"}})
            self.fail("expected error")
        except TypeError:
            pass

    def test_explore_filter_set_fields(self):
        concepts = {
            "concepts": ["a"],
        }
        e = Explore(concepts)
        self.assertEqual('{concepts: ["a"] }', str(e))

        concepts = {
            "concepts": "a",
        }
        e = Explore(concepts)
        self.assertEqual('{concepts: "a" }', str(e))

        concepts = {
            "concepts": "a",
            "certainty": 0.6
        }
        e = Explore(concepts)
        self.assertEqual('{concepts: "a" certainty: 0.6 }', str(e))

        concepts = {
            "concepts": "a",
            "moveTo": {
                "concepts": "b",
                "force": 0.2
            },
        }
        e = Explore(concepts)
        self.assertEqual('{concepts: "a" moveTo:{concepts: "b" force: 0.2} }', str(e))

        concepts = {
            "concepts": "a",
            "moveAwayFrom": {
                "concepts": ["c"],
                "force": 0.5
            },
        }
        e = Explore(concepts)
        self.assertEqual('{concepts: "a" moveAwayFrom:{concepts: ["c"] force: 0.5} }', str(e))

        concepts = {
            "concepts": ["a"],
            "moveTo": {
                "concepts": "b",
                "force": 0.2
            },
            "moveAwayFrom": {
                "concepts": ["c"],
                "force": 0.3
            },
            "certainty": 0.6
        }
        e = Explore(concepts)
        self.assertEqual('{concepts: ["a"] certainty: 0.6 moveTo:{concepts: "b" force: 0.2} moveAwayFrom:{concepts: ["c"] force: 0.3} }', str(e))


