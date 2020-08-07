import unittest
from weaviate.gql.builder import *


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
        Get.things("Person", "{name}").with_where(filter).do()

