"""In-Pyodide e2e for the Weaviate client over core-native grpc-web.

Executed by ``run.mjs`` inside Pyodide under Node: the runner runs this module's code
(imports below install the grpc shim + fetch transport) and then awaits ``main()`` on
Pyodide's event loop. Plain asserts with one ``OK`` line per step so CI logs are
diagnosable; any failure exits nonzero.

Deliberately not covered: browser/CORS behaviour (this runs under Node, no CORS layer)
and OIDC auth flows (anonymous access only).
"""

import os
import uuid
import warnings

import weaviate_client_web  # bootstraps the grpc shim + fetch transport under Emscripten

import grpc
import httpx
import weaviate
import weaviate.classes as wvc
from weaviate.classes.config import DataType, Property, ReferenceProperty
from weaviate.classes.data import DataReference
from weaviate.classes.query import Filter
from weaviate.classes.tenants import Tenant
from weaviate.exceptions import WeaviateBatchStreamError, WeaviateQueryError

COLL = "PyodideE2E"
MT_COLL = "PyodideE2ETenants"
# Weaviate core serves grpc-web natively on the REST port under this prefix (default-on
# since 1.38.3), so no proxy sits between the client and the server. Under Emscripten the
# connect helpers route gRPC there themselves — nothing here selects it.
GRPC_WEB_PREFIX = "/v1/grpc-web"


def ok(step: str) -> None:
    print(f"OK {step}", flush=True)


async def main() -> None:
    assert weaviate_client_web.is_installed(), "grpc shim did not install under Emscripten"
    assert getattr(grpc, "__weaviate_client_web_shim__", False), (
        "sys.modules['grpc'] is not the shim"
    )
    # REST must run through the package's own fetch transport, not Pyodide's bundled
    # httpx transport (which cannot read the null body of HEAD / 204 responses).
    assert weaviate_client_web.is_fetch_transport_installed(), "fetch transport not installed"
    assert getattr(
        httpx.AsyncHTTPTransport.handle_async_request, "__weaviate_fetch_shim__", False
    ), "httpx.AsyncHTTPTransport is not the package's fetch transport"
    ok("self-check: package fetch transport is the active httpx transport")

    host = os.environ.get("WEAVIATE_HOST", "localhost")
    port = int(os.environ.get("WEAVIATE_PORT", "8090"))
    client = weaviate.use_async_with_custom(
        http_host=host,
        http_port=port,
        http_secure=False,
        grpc_host=host,
        grpc_port=port,
        grpc_secure=False,
    )
    params = client._connection._connection_params
    assert params._grpc_web_path_prefix == GRPC_WEB_PREFIX, params
    assert params._grpc_target == f"{host}:{port}", params
    ok("connect helper routed gRPC onto the REST endpoint under /v1/grpc-web")

    # No skip_init_checks: connect() performs the gRPC health check over grpc-web.
    await client.connect()
    ok("connect (health check over grpc-web)")

    try:
        for name in (COLL, MT_COLL):
            if await client.collections.exists(name):
                await client.collections.delete(name)

        await client.collections.create(
            COLL,
            vector_config=wvc.config.Configure.Vectors.self_provided(),
            properties=[
                Property(name="title", data_type=DataType.TEXT),
                Property(name="idx", data_type=DataType.INT),
            ],
            references=[ReferenceProperty(name="related", target_collection=COLL)],
        )
        ok("collections.create")

        coll = client.collections.get(COLL)
        ret = await coll.data.insert_many([{"title": f"article {i}", "idx": i} for i in range(50)])
        assert not ret.has_errors and len(ret.uuids) == 50, f"insert_many errors: {ret.errors}"
        ok("insert_many (BatchObjects) = 50")

        res = await coll.query.fetch_objects(limit=100)
        assert len(res.objects) == 50, f"fetch_objects got {len(res.objects)}"
        ok("query.fetch_objects = 50")

        res = await coll.query.bm25("article", limit=5)
        assert len(res.objects) == 5, f"bm25 got {len(res.objects)}"
        ok("query.bm25 limit=5 = 5")

        res = await coll.query.fetch_objects(
            filters=Filter.by_property("idx").less_than(10), limit=100
        )
        assert len(res.objects) == 10, f"filtered fetch_objects got {len(res.objects)}"
        ok("query.fetch_objects filtered idx<10 = 10")

        agg = await coll.aggregate.over_all(total_count=True)
        assert agg.total_count == 50, f"aggregate total_count {agg.total_count}"
        agg = await coll.aggregate.over_all(
            return_metrics=[wvc.query.Metrics("idx").integer(minimum=True, maximum=True)]
        )
        idx = agg.properties["idx"]
        assert idx.minimum == 0 and idx.maximum == 49, agg.properties
        ok("aggregate count=50 min=0 max=49")

        # REST calls answered without a body (HEAD 204/404, PATCH/DELETE 204) and the
        # batch-references path, which reads httpx's response.elapsed.
        first, second, last = ret.uuids[0], ret.uuids[1], ret.uuids[49]
        assert await coll.data.exists(first) is True
        assert await coll.data.exists(uuid.uuid4()) is False
        ok("data.exists (HEAD 204 / 404) = True / False")

        await coll.data.update(uuid=first, properties={"title": "article 0 (updated)"})
        obj = await coll.query.fetch_object_by_id(first)
        assert obj is not None and obj.properties["title"] == "article 0 (updated)", obj
        ok("data.update (PATCH 204) -> fetch_object_by_id sees the update")

        refs = await coll.data.reference_add_many(
            [
                DataReference(
                    from_property="related", from_uuid=ret.uuids[i], to_uuid=ret.uuids[i + 1]
                )
                for i in range(5)
            ]
        )
        assert not refs.has_errors, f"reference_add_many errors: {refs.errors}"
        assert refs.elapsed_seconds >= 0, refs
        ok("data.reference_add_many (REST /batch/references) = 5")

        await coll.data.reference_delete(from_uuid=first, from_property="related", to=second)
        ok("data.reference_delete (DELETE 204)")

        assert await coll.data.delete_by_id(last) is True
        assert await coll.data.exists(last) is False
        # deleting a missing object answers 204 or 404 depending on the server topology;
        # either way it is a body-less response the transport must handle
        assert isinstance(await coll.data.delete_by_id(last), bool)
        ok("data.delete_by_id (DELETE 204; repeat -> 204/404) = True, then bool")

        await client.collections.create(
            MT_COLL,
            vector_config=wvc.config.Configure.Vectors.self_provided(),
            properties=[Property(name="title", data_type=DataType.TEXT)],
            multi_tenancy_config=wvc.config.Configure.multi_tenancy(enabled=True),
        )
        mt = client.collections.get(MT_COLL)
        await mt.tenants.create([Tenant(name="t1"), Tenant(name="t2")])
        tenants = await mt.tenants.get()
        assert set(tenants.keys()) == {"t1", "t2"}, f"TenantsGet: {set(tenants.keys())}"
        ok("multi-tenant create + TenantsGet = {t1, t2}")

        assert await mt.tenants.exists("t1") is True
        assert await mt.tenants.exists("t404") is False
        ok("tenants.exists (HEAD 200 / 404) = True / False")

        t1 = mt.with_tenant("t1")
        ret = await t1.data.insert_many([{"title": f"tenant doc {i}"} for i in range(10)])
        assert not ret.has_errors and len(ret.uuids) == 10, f"tenant insert_many: {ret.errors}"
        agg = await t1.aggregate.over_all(total_count=True)
        assert agg.total_count == 10, f"tenant aggregate {agg.total_count}"
        ok("per-tenant insert_many = 10, aggregate = 10")

        dm = await t1.data.delete_many(where=Filter.by_property("title").like("tenant*"))
        assert dm.successful == 10, f"delete_many successful={dm.successful}"
        agg = await t1.aggregate.over_all(total_count=True)
        assert agg.total_count == 0, f"post-delete aggregate {agg.total_count}"
        ok("per-tenant delete_many (BatchDelete) = 10 -> aggregate = 0")

        try:
            await client.collections.get("DoesNotExistXyz").query.fetch_objects(limit=1)
            raise AssertionError("expected WeaviateQueryError for nonexistent collection")
        except WeaviateQueryError as e:
            assert "DoesNotExistXyz" in str(e), str(e)
        ok("error mapping: nonexistent collection -> WeaviateQueryError names the collection")

        try:
            async with client.batch.stream() as batch:
                await batch.add_object(collection=COLL, properties={"title": "x", "idx": 999})
            raise AssertionError("batch.stream() did not raise under grpc-web")
        except WeaviateBatchStreamError as e:
            assert "grpc-web" in str(e) and "insert_many" in str(e), str(e)
        ok("batch.stream() -> WeaviateBatchStreamError (clear message)")

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                async with client.batch.experimental() as batch:
                    await batch.add_object(collection=COLL, properties={"title": "x", "idx": 999})
            raise AssertionError("batch.experimental() did not raise under grpc-web")
        except WeaviateBatchStreamError:
            ok("batch.experimental() -> WeaviateBatchStreamError")

        for name in (COLL, MT_COLL):
            await client.collections.delete(name)
        ok("cleanup")
    finally:
        await client.close()

    print("PYODIDE E2E: ALL STEPS OK", flush=True)
