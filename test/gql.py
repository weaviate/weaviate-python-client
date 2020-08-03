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

