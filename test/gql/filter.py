import unittest
from weaviate.gql.filter import *


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
