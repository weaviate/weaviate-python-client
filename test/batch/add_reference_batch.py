import unittest
from unittest.mock import Mock
from test.testing_util import replace_connection, add_run_rest_to_mock

import weaviate
from weaviate import SEMANTIC_TYPE_ACTIONS, SEMANTIC_TYPE_THINGS
from weaviate.connect import REST_METHOD_POST


class TestBatchReferencesObject(unittest.TestCase):

    def test_batch_length(self):
        batch = weaviate.ReferenceBatchRequest()

        batch.add_reference("04a4b17d-6beb-443a-b1bc-835b0dd4e660", "Alpha", "a",
                            "fc7eb129-f138-457f-b727-1b29db191a67", SEMANTIC_TYPE_THINGS, SEMANTIC_TYPE_THINGS)
        self.assertEqual(1, len(batch))
        batch.add_reference("fd5af656-7d86-40da-9577-845c98e75543", "Alpha", "a",
                            "1c51b14d-1652-4225-8dfc-7f4079616f65", SEMANTIC_TYPE_THINGS, SEMANTIC_TYPE_THINGS)
        self.assertEqual(2, len(batch))
        batch.add_reference("85178ffb-0825-4f7d-98d3-2efc85796889", "Alpha", "a",
                            "aeb937d8-546c-44fe-bc5c-e11d93970ccd", SEMANTIC_TYPE_THINGS, SEMANTIC_TYPE_THINGS)
        self.assertEqual(3, len(batch))

    def test_batch_add_url(self):
        batch = weaviate.ReferenceBatchRequest()
        batch.add_reference("weaviate://localhost/things/04a4b17d-6beb-443a-b1bc-835b0dd4e660",
                            "Alpha",
                            "a",
                            "weaviate://localhost/things/fc7eb129-f138-457f-b727-1b29db191a67",
                            SEMANTIC_TYPE_THINGS,
                            SEMANTIC_TYPE_THINGS)
        self.assertEqual(1, len(batch))
        self.assertEqual("04a4b17d-6beb-443a-b1bc-835b0dd4e660", batch._from_entity_ids[0])
        self.assertEqual("fc7eb129-f138-457f-b727-1b29db191a67", batch._to_entity_ids[0])

    def test_batch_add_reference(self):
        # 1. from thing to thing
        batch = weaviate.ReferenceBatchRequest()
        batch.add_reference("fd5af656-7d86-40da-9577-845c98e75543", "Griptape", "color",
                            "1c51b14d-1652-4225-8dfc-7f4079616f65", SEMANTIC_TYPE_THINGS, SEMANTIC_TYPE_THINGS)
        body = batch.get_request_body()
        self.assertEqual("weaviate://localhost/things/Griptape/fd5af656-7d86-40da-9577-845c98e75543/color",
                         body[0]["from"])
        self.assertEqual("weaviate://localhost/things/1c51b14d-1652-4225-8dfc-7f4079616f65",
                         body[0]["to"])

        # 2. from action to action
        batch.add_reference("85178ffb-0825-4f7d-98d3-2efc85796889", "Truck", "material",
                            "aeb937d8-546c-44fe-bc5c-e11d93970ccd", SEMANTIC_TYPE_ACTIONS, SEMANTIC_TYPE_ACTIONS)
        body = batch.get_request_body()
        self.assertEqual("weaviate://localhost/actions/Truck/85178ffb-0825-4f7d-98d3-2efc85796889/material",
                         body[1]["from"])
        self.assertEqual("weaviate://localhost/actions/aeb937d8-546c-44fe-bc5c-e11d93970ccd",
                         body[1]["to"])

        # 3. from action to thing
        batch.add_reference("85178ffb-0825-4f7d-98d3-2efc85796889", "Truck", "material",
                            "aeb937d8-546c-44fe-bc5c-e11d93970ccd", SEMANTIC_TYPE_ACTIONS, SEMANTIC_TYPE_THINGS)
        body = batch.get_request_body()
        self.assertEqual("weaviate://localhost/actions/Truck/85178ffb-0825-4f7d-98d3-2efc85796889/material",
                         body[2]["from"])
        self.assertEqual("weaviate://localhost/things/aeb937d8-546c-44fe-bc5c-e11d93970ccd",
                         body[2]["to"])


class TestAddReferencesBatch(unittest.TestCase):

    def test_add_references_in_batch(self):
        w = weaviate.Client("http://test-add-references")

        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock)
        replace_connection(w, connection_mock)

        batch = weaviate.ReferenceBatchRequest()
        batch.add_reference("431c13e7-7479-45ac-a956-29ef6c662a9e", "Product", "parts",
                            "1d5c8296-d24e-4e4b-b0e8-9e7e1b40bfb1")
        batch.add_reference("715de36c-e528-47c2-a5ee-73cccadacbc0", "Product", "parts",
                            "465533f8-f0af-4f53-a51b-35a885423e6a", from_semantic_type=SEMANTIC_TYPE_ACTIONS)

        w.batch.add_references(batch)

        connection_mock.run_rest.assert_called()

        call_args_list = connection_mock.run_rest.call_args_list
        call_args, call_kwargs = call_args_list[0]

        self.assertEqual("/batching/references", call_args[0])
        self.assertEqual(REST_METHOD_POST, call_args[1])


