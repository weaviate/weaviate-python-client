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

For REST, Pyodide ≥ 0.27 distributes a patched httpx that already routes through the
browser's `fetch` natively — when that build is detected the package leaves it alone.
Only when httpx resolved from PyPI (httpcore + raw sockets, which cannot work under
WASM) does the package patch `httpx.AsyncHTTPTransport` with its own pyfetch-based
transport.

## Usage

With this package installed, a plain `import weaviate` is all you need — under
Emscripten the base client imports `weaviate_grpc_web` itself before anything else,
which installs the shim (and raises a clear error if the package is missing):

```python
import weaviate  # bootstraps weaviate_grpc_web automatically under Emscripten

client = weaviate.use_async_with_local(skip_init_checks=True)
await client.connect()
collection = client.collections.get("Article")
await collection.query.near_text("hello", limit=3)
```

Importing the companion explicitly first also works and remains the explicit form:

```python
import weaviate_grpc_web   # installs the grpc shim under Emscripten (no-op elsewhere)
import weaviate
```

## Supported / unsupported

| Feature                                                   | Kind            | Status |
|----------------------------------------------------------|-----------------|--------|
| Search, Aggregate, TenantsGet, BatchObjects, BatchDelete | unary gRPC      | ✅ works over grpc-web |
| Health check (`/grpc.health.v1.Health/Check`)            | unary gRPC      | ✅ (recommend `skip_init_checks=True` + REST `/.well-known/ready`) |
| REST (`is_ready`, config, `/batch/references`, …)         | REST            | ✅ via fetch (Pyodide's httpx build, or this package's fallback transport) |
| API-key auth (`Auth.api_key`)                             | header          | ✅ |
| OIDC auth (`client_credentials` / `client_password` / `bearer_token`) | REST | ✅ token fetch + asyncio-task refresh (no threads) |
| Bulk insert: `collection.data.insert_many()`              | unary gRPC      | ✅ the supported bulk path under WASM |
| `batch.stream()` / `batch.experimental()` (BatchStream)  | bidi streaming  | ❌ not possible over grpc-web/fetch — raises immediately; use `insert_many()` |
| `batch.dynamic()` / `fixed_size()` / `rate_limit()`      | sync-client API | ❌ these only exist on the sync client, which is unsupported under WASM |
| Embedded Weaviate (`use_async_with_embedded`)            | subprocess      | ❌ raises "not supported under WebAssembly/Pyodide" |
| Synchronous client                                       | —               | ❌ async-only under WASM |
| Weaviate Agents: `AsyncQueryAgent` `run/ask/search`      | REST            | ✅ via fetch |
| Weaviate Agents: `ask_stream` / `research_stream` (SSE)  | REST streaming  | ⚠️ degraded under the fallback transport: fully buffered, events arrive only when the run completes (and long runs can hit the request timeout) |
| Weaviate Agents: sync `QueryAgent`, `TransformationAgent`, `PersonalizationAgent` | REST sync | ❌ no async flavour exists |

## Configuration not honored in the browser

`fetch` manages connections itself, so several knobs are accepted but have no effect
under WASM:

- `AdditionalConfig.proxies` / `trust_env` proxy environment variables (the browser
  cannot proxy fetch requests per-client),
- connection-pool sizing and `session_pool_max_retries`,
- `GrpcConfig.credentials` (custom CA bundles — the browser's trust store decides TLS),
- `GrpcConfig.channel_options`, including `grpc.max_send/receive_message_length`
  (only `grpc-web.path_prefix` is consumed),
- `Proxies.grpc` / `GRPC_PROXY`.

## CORS requirements (browsers)

Cross-origin browser deployments must configure the grpc-web transcoder / REST endpoint
with CORS, or failures become hard to diagnose:

- allow the request headers the client sends: `authorization`, `content-type`,
  `x-grpc-web`, and any custom headers;
- expose the grpc-web status headers on responses:
  `Access-Control-Expose-Headers: grpc-status, grpc-message` — without this,
  trailers-only error responses (e.g. a bad API key) are reported as
  `INTERNAL: grpc-web response contained no message frame` instead of the real error;
- note that a CORS-blocked request is indistinguishable from a network failure in the
  browser (`TypeError: Failed to fetch`), and is retried as UNAVAILABLE.

## Testing on CPython

`weaviate_grpc_web.install(force=True)` installs the shim on a normal CPython
interpreter (run it in a fresh process, before importing `weaviate`). Inject a sender
with `weaviate_grpc_web.set_sender(...)` (e.g. `make_httpx_sender()`) to exercise the
transport against an Envoy/vanguard transcoder without a browser.
