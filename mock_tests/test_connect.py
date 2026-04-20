import time
import pytest
import weaviate
from weaviate.proto.v1 import batch_pb2


def test_bidi_stream_cancel_sync(stream_cancel: weaviate.collections.Collection):
    def gen():
        time.sleep(10)
        yield batch_pb2.BatchStreamRequest()

    out, call = stream_cancel._connection.grpc_batch_stream(gen())
    assert call.is_active()
    call.cancel()
    assert not call.is_active()
    with pytest.raises(weaviate.exceptions.WeaviateBatchStreamError) as e:
        next(out)
    assert "StatusCode.CANCELLED(Locally cancelled by application!)" in e.value.message


def test_batch_stream_hanging_server(stream_cancel: weaviate.collections.Collection):
    with pytest.raises(weaviate.exceptions.WeaviateBatchStreamError) as e:
        with stream_cancel.batch.stream() as batch:
            batch.add_object()
    assert "The server did not hangup its side of the stream gracefully in time" in e.value.message
