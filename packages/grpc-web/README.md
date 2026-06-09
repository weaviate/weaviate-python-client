# weaviate-python-grpc-web

A grpc-web / WebAssembly (Pyodide) transport for the
[Weaviate Python client](https://github.com/weaviate/weaviate-python-client), so the
client's **async** gRPC data path can run inside a browser (marimo notebooks, Pyodide,
WASM workers) where there is no socket and no `grpcio` wheel.

It is built from the same repository as `weaviate-client` and reuses its generated
protobuf stubs — it does **not** fork code generation.

## How it works

Under Pyodide there is no `grpcio` Emscripten wheel, and `import weaviate` hard-imports
`grpc` at module load. This package installs a small pure-Python `grpc` shim into
`sys.modules` **before** `import weaviate`, which:

- satisfies every import-time `import grpc` / `from grpc(.aio) import ...` in the base
  client and its generated `*_pb2_grpc` stubs;
- provides `grpc.aio.Channel` as a real base class, so the grpc-web channel
  (`GrpcWebChannel`) subclasses it and the client's `isinstance(..., grpc.aio.Channel)`
  assertions pass;
- satisfies the generated v6300 stub's version gate
  (`grpc.__version__` / `grpc._utilities.first_version_is_lower`).

The `GrpcWebChannel` frames unary RPCs as grpc-web (a 5-byte header + protobuf payload)
and POSTs them via `pyodide.http.pyfetch` to a server fronted by a grpc-web transcoder
(e.g. Envoy or [connectrpc/vanguard](https://github.com/connectrpc/vanguard-go)). Call
metadata (API key / OIDC bearer) is folded into `fetch` headers.

## Usage

```python
import weaviate_grpc_web   # installs the grpc shim under Emscripten (no-op elsewhere)
import weaviate

client = weaviate.use_async_with_local(skip_init_checks=True)
await client.connect()
collection = client.collections.get("Article")
await collection.query.near_text("hello", limit=3)
```

## Supported / unsupported

| RPC                                                       | Kind            | Status |
|----------------------------------------------------------|-----------------|--------|
| Search, Aggregate, TenantsGet, BatchObjects, BatchDelete | unary           | ✅ works over grpc-web |
| Health check (`/grpc.health.v1.Health/Check`)            | unary           | ✅ (recommend `skip_init_checks=True` + REST `/.well-known/ready`) |
| References (`/batch/references`)                          | REST            | ✅ via httpx-in-Pyodide |
| `batch.stream()` / `batch.experimental()` (BatchStream)  | bidi streaming  | ❌ not possible over grpc-web/fetch — use `insert_many()` / `batch.dynamic()` / `fixed_size()` / `rate_limit()` |
| Synchronous client                                       | —               | ❌ async-only under WASM |

## Testing on CPython

`weaviate_grpc_web.install(force=True)` installs the shim on a normal CPython
interpreter (run it in a fresh process, before importing `weaviate`). Inject a sender
with `weaviate_grpc_web.set_sender(...)` (e.g. `make_httpx_sender()`) to exercise the
transport against an Envoy/vanguard transcoder without a browser.
