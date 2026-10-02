import warnings
import weaviate
from weaviate.collections.classes.batch import ErrorObject
from weaviate.proto.v1 import batch_pb2, weaviate_pb2_grpc
from .conftest import MOCK_IP, MOCK_PORT, MOCK_PORT_GRPC, mock_class


class Svc(weaviate_pb2_grpc.WeaviateServicer):
    calls = 0

    def BatchObjects(self, request, context):
        self.calls += 1
        if self.calls == 2:  # second chunk, once: rate-limit its first object
            return batch_pb2.BatchObjectsReply(errors=[{"index": 0, "error": "failed with status: 503 error"}])
        return batch_pb2.BatchObjectsReply()


def test_readd_no_stale_errors_and_no_dep020(weaviate_mock, start_grpc_server):
    """Re-adding rate-limited objects must not leave stale errors behind, and
    the internal re-add path must not trigger the deprecated
    ``all_responses`` property's Dep020 warning (issue #2179)."""
    weaviate_mock.expect_request(f"/v1/schema/{mock_class['class']}").respond_with_json(mock_class)
    weaviate_pb2_grpc.add_WeaviateServicer_to_server(Svc(), start_grpc_server)
    client = weaviate.connect_to_local(port=MOCK_PORT, host=MOCK_IP, grpc_port=MOCK_PORT_GRPC)
    try:
        col = client.collections.use(mock_class["class"])
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            with col.batch.fixed_size(batch_size=2, concurrent_requests=1) as b:
                for i in range(4):
                    b.add_object({"name": f"o{i}"})
        r = col.batch.results.objs
        dep = [x for x in w if "all_responses" in str(x.message)]
        stale = [x for x in r._all_responses if isinstance(x, ErrorObject)]
        assert len(dep) == 0, f"deprecated all_responses read during batch: {[str(x.message)[:60] for x in dep]}"
        assert len(r.errors) == 0
        assert len(stale) == 0, f"stale errors left behind: {[e.message for e in stale]}"
        assert len(r._all_responses) == 4
    finally:
        client.close()
