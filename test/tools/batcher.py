import unittest
from unittest.mock import Mock
from weaviate.tools import Batcher
import uuid


class TestBatcher(unittest.TestCase):

    def test_batcher_add_thing(self):
        client_mock = Mock()
        batcher = Batcher(client_mock, 3)

        batcher.add_thing({}, "MyClass", str(uuid.uuid4()))
        batcher.add_thing({}, "MyClass", str(uuid.uuid4()))
        self.assertEqual(2, len(batcher._things_batch))
        assert not client_mock.create_things_in_batch.called
        # With the next thing the batcher should create the batch
        batcher.add_thing({}, "MyClass", str(uuid.uuid4()))
        assert client_mock.create_things_in_batch.called
        # check if batch is being reset
        self.assertEqual(0, len(batcher._things_batch))

    def test_batcher_add_reference(self):
        client_mock = Mock()
        batcher = Batcher(client_mock, 3)

        batcher.add_reference("FromClass", str(uuid.uuid4()), "fromProperty", str(uuid.uuid4()))
        batcher.add_reference("FromClass", str(uuid.uuid4()), "fromProperty", str(uuid.uuid4()))
        self.assertEqual(2, len(batcher._reference_batch))
        assert not client_mock.add_references_in_batch.called
        # With the next reference the batcher should create the batch
        batcher.add_reference("FromClass", str(uuid.uuid4()), "fromProperty", str(uuid.uuid4()))
        assert client_mock.add_references_in_batch.called
        # check if batch is being reset
        self.assertEqual(0, len(batcher._reference_batch))

    def test_batcher_close(self):
        client_mock = Mock()
        batcher = Batcher(client_mock, 3)

        batcher.add_reference("FromClass", str(uuid.uuid4()), "fromProperty", str(uuid.uuid4()))
        batcher.add_reference("FromClass", str(uuid.uuid4()), "fromProperty", str(uuid.uuid4()))
        batcher.close()
        assert client_mock.add_references_in_batch.called

    def test_batcher_force_update(self):
        client_mock = Mock()
        batcher = Batcher(client_mock, 3)

        batcher.add_reference("FromClass", str(uuid.uuid4()), "fromProperty", str(uuid.uuid4()))
        batcher.add_reference("FromClass", str(uuid.uuid4()), "fromProperty", str(uuid.uuid4()))
        batcher.update_batches()
        assert client_mock.add_references_in_batch.called

    def test_with_batcher(self):
        with Batcher()

