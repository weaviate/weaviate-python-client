"""In-Pyodide e2e for the Weaviate client over core-native grpc-web.

Executed by ``run.mjs`` inside Pyodide under Node: the runner runs this module's code
(imports below install the grpc shim + fetch transport) and then awaits ``main()`` on
Pyodide's event loop. Plain asserts with one ``OK`` line per step so CI logs are
diagnosable; any failure exits nonzero.

Deliberately not covered: browser/CORS behaviour (this runs under Node, no CORS layer)
and OIDC auth flows (anonymous access only).
"""

import os
import warnings

import weaviate_client_web  # bootstraps the grpc shim + fetch transport under Emscripten

import grpc
import weaviate
import weaviate.classes as wvc
from weaviate.classes.config import DataType, Property
from weaviate.classes.query import Filter
from weaviate.classes.tenants import Tenant
from weaviate.exceptions import WeaviateBatchStreamError, WeaviateQueryError

COLL = "PyodideE2E"
MT_COLL = "PyodideE2ETenants"
# Weaviate core serves grpc-web natively on the REST port under this prefix
# (default-on since 1.38.3), so no proxy sits between the client and the server.
GRPC_WEB_PREFIX = "/v1/grpc-web"


def ok(step: str) -> None:
    print(f"OK {step}", flush=True)


async def main() -> None:
    assert weaviate_client_web.is_installed(), "grpc shim did not install under Emscripten"
    assert getattr(grpc, "__weaviate_client_web_shim__", False), (
        "sys.modules['grpc'] is not the shim"
    )

    host = os.environ.get("WEAVIATE_HOST", "localhost")
    port = int(os.environ.get("WEAVIATE_PORT", "8090"))
    client = weaviate.use_async_with_custom(
        http_host=host,
        http_port=port,
        http_secure=False,
        grpc_host=host,
        grpc_port=port,
        grpc_secure=False,
        grpc_path_prefix=GRPC_WEB_PREFIX,
    )
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
            assert "DoesNotExistXyz" in str(e) or "not" in str(e).lower(), str(e)
        ok("error mapping: nonexistent collection -> WeaviateQueryError")

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
