import unittest
import weaviate
from weaviate.connect import REST_METHOD_POST
from test.testing_util import *


class TestReferences(unittest.TestCase):

    def test_batch_length(self):
        batch = weaviate.ReferenceBatchRequest()

        batch.add_reference("Alpha", "04a4b17d-6beb-443a-b1bc-835b0dd4e660",
                            "a", "fc7eb129-f138-457f-b727-1b29db191a67")
        self.assertEqual(1, len(batch))
        batch.add_reference("Alpha", "fd5af656-7d86-40da-9577-845c98e75543",
                            "a", "1c51b14d-1652-4225-8dfc-7f4079616f65")
        self.assertEqual(2, len(batch))
        batch.add_reference("Alpha", "85178ffb-0825-4f7d-98d3-2efc85796889",
                            "a", "aeb937d8-546c-44fe-bc5c-e11d93970ccd")
        self.assertEqual(3, len(batch))

    def test_batch_add_url(self):
        batch = weaviate.ReferenceBatchRequest()
        batch.add_reference("Alpha", "weaviate://localhost/things/04a4b17d-6beb-443a-b1bc-835b0dd4e660",
                            "a", "weaviate://localhost/things/fc7eb129-f138-457f-b727-1b29db191a67")
        self.assertEqual(1, len(batch))
        self.assertEqual("04a4b17d-6beb-443a-b1bc-835b0dd4e660", batch._from_thing_ids[0])
        self.assertEqual("fc7eb129-f138-457f-b727-1b29db191a67", batch._to_thing_ids[0])