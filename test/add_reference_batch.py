import unittest
import weaviate
from weaviate import SEMANTIC_TYPE_ACTIONS, SEMANTIC_TYPE_THINGS


class TestReferences(unittest.TestCase):

    def test_batch_length(self):
        batch = weaviate.ReferenceBatchRequest()

        batch.add_reference(SEMANTIC_TYPE_THINGS, "Alpha", "04a4b17d-6beb-443a-b1bc-835b0dd4e660",
                            "a", SEMANTIC_TYPE_THINGS, "fc7eb129-f138-457f-b727-1b29db191a67")
        self.assertEqual(1, len(batch))
        batch.add_reference(SEMANTIC_TYPE_THINGS, "Alpha", "fd5af656-7d86-40da-9577-845c98e75543",
                            "a", SEMANTIC_TYPE_THINGS, "1c51b14d-1652-4225-8dfc-7f4079616f65")
        self.assertEqual(2, len(batch))
        batch.add_reference(SEMANTIC_TYPE_THINGS, "Alpha", "85178ffb-0825-4f7d-98d3-2efc85796889",
                            "a", SEMANTIC_TYPE_THINGS, "aeb937d8-546c-44fe-bc5c-e11d93970ccd")
        self.assertEqual(3, len(batch))

    def test_batch_add_url(self):
        batch = weaviate.ReferenceBatchRequest()
        batch.add_reference(SEMANTIC_TYPE_THINGS, "Alpha",
                            "weaviate://localhost/things/04a4b17d-6beb-443a-b1bc-835b0dd4e660",
                            SEMANTIC_TYPE_THINGS, "a",
                            "weaviate://localhost/things/fc7eb129-f138-457f-b727-1b29db191a67")
        self.assertEqual(1, len(batch))
        self.assertEqual("04a4b17d-6beb-443a-b1bc-835b0dd4e660", batch._from_entity_ids[0])
        self.assertEqual("fc7eb129-f138-457f-b727-1b29db191a67", batch._to_entity_ids[0])

    def test_batch_add_reference(self):
        # 1. from thing to thing
        batch = weaviate.ReferenceBatchRequest()
        batch.add_reference(SEMANTIC_TYPE_THINGS, "Griptape", "fd5af656-7d86-40da-9577-845c98e75543", "color", SEMANTIC_TYPE_THINGS, "1c51b14d-1652-4225-8dfc-7f4079616f65")
        body = batch.get_request_body()
        self.assertEqual("weaviate://localhost/things/Griptape/fd5af656-7d86-40da-9577-845c98e75543/color",
                         body[0]["from"])
        self.assertEqual("weaviate://localhost/things/1c51b14d-1652-4225-8dfc-7f4079616f65",
                         body[0]["to"])

        # 2. from action to action
        batch.add_reference(SEMANTIC_TYPE_ACTIONS, "Truck", "85178ffb-0825-4f7d-98d3-2efc85796889", "material",
                            SEMANTIC_TYPE_ACTIONS, "aeb937d8-546c-44fe-bc5c-e11d93970ccd")
        body = batch.get_request_body()
        self.assertEqual("weaviate://localhost/actions/Truck/85178ffb-0825-4f7d-98d3-2efc85796889/material",
                         body[1]["from"])
        self.assertEqual("weaviate://localhost/actions/aeb937d8-546c-44fe-bc5c-e11d93970ccd",
                         body[1]["to"])

        # 3. from action to thing
        batch.add_reference(SEMANTIC_TYPE_ACTIONS, "Truck", "85178ffb-0825-4f7d-98d3-2efc85796889", "material",
                            SEMANTIC_TYPE_THINGS, "aeb937d8-546c-44fe-bc5c-e11d93970ccd")
        body = batch.get_request_body()
        self.assertEqual("weaviate://localhost/actions/Truck/85178ffb-0825-4f7d-98d3-2efc85796889/material",
                         body[2]["from"])
        self.assertEqual("weaviate://localhost/things/aeb937d8-546c-44fe-bc5c-e11d93970ccd",
                         body[2]["to"])