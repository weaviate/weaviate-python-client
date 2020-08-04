import unittest
from weaviate.gql import *


class TestGraphQL(unittest.TestCase):

    def test_builder(self):

        filter = {
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
        Get.things("Person", "{name}").with_filter(filter).do()

    def test_build_simple_query(self):
        query = Get.things("Group", "{name}").do()
        query = query.strip()
        self.assertEqual("{Get{Things{Group{name}}}}", query)

    def test_filter_inputs(self):
        self._expect_filter_error("", TypeError)
        filter = {
            "path": ["name"],
            "operator": "Equal",
        }
        self._expect_filter_error(filter, ValueError)
        filter = {
            "path": ["name"],
            "valueString": "John von Neumann"
        }
        self._expect_filter_error(filter, ValueError)
        filter = {
            "operator": "Equal",
            "valueString": "John von Neumann"
        }
        self._expect_filter_error(filter, ValueError)
        filter = {
            "operands": []
        }
        self._expect_filter_error(filter, ValueError)

    def _expect_filter_error(self, filter, expected_error):
        try:
            Filter(filter)
            self.fail()
        except expected_error:
            pass
