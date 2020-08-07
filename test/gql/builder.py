import unittest
from weaviate.gql.builder import *


class TestGraphQLBuilder(unittest.TestCase):

    def test_build_input(self):
        try:
            Get.things(1, ["a"]).do()
            self.fail("expected error")
        except TypeError:
            pass
        try:
            Get.things("A", 2).do()
            self.fail("expected error")
        except TypeError:
            pass

    def test_build_simple_query(self):
        query = Get.things("Group", "name").do()
        self.assertEqual("{Get{Things{Group{name}}}}", query)

        query = Get.things("Group", ["name", "uuid"]).do()
        self.assertEqual("{Get{Things{Group{name uuid}}}}", query)

    def test_build_limited_query(self):
        query = Get.things("Person", "name").with_limit(20).do()
        self.assertEqual('{Get{Things{Person(limit: 20 ){name}}}}', query)

    def test_build_where_limited_query(self):
        filter = {
            "path": ["name"],
            "operator": "Equal",
            "valueString": "A"
        }
        query = Get.things("Person", "{name}").with_limit(1).with_where(filter).do()
        self.assertEqual('{Get{Things{Person(where:{path: ["name"] operator: Equal valueString: "A"} limit: 1 ){name}}}}', query)

    def test_build_explore_query(self):
        explore = {
            "concepts": "computer",
            "moveTo": {
                "concepts": ["science"],
                "force": 0.5
            },
        }
        query = Get.things("Person", "{name}").with_explore(explore).do()
        self.assertEqual('{Get{Things{Person(explore:{concepts: "computer" moveTo:{concepts: ["science"] force: 0.5} } ){name}}}}', query)

    def test_build_full_query(self):
        explore = {
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
        query = Get.things("Person", ["name", "uuid"]).with_explore(explore).with_where(filter).with_limit(2).do()
        self.assertEqual('{Get{Things{Person(where: {operator: Or operands: [{path: ["name"] operator: Equal valueString: "Alan Turing"}, {path: ["name"] operator: Equal valueString: "John von Neumann"}]} limit: 2 explore:{concepts: ["computer"] certainty: 0.3 moveTo:{concepts: "science" force: 0.1} moveAwayFrom:{concepts: ["airplane"] force: 0.2} } ){name uuid}}}}', query)