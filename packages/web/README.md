# weaviate-client-web

A grpc-web / WebAssembly (Pyodide) transport for the
[Weaviate Python client](https://github.com/weaviate/weaviate-python-client), so the
client's **async** gRPC data path can run inside a browser (marimo notebooks, Pyodide,
WASM workers) where there is no socket and no `grpcio` wheel.

It is built from the same repository as `weaviate-client` and reuses its generated
protobuf stubs — it does **not** fork code generation.

Requires Weaviate ≥ 1.38.3 (the first release to serve grpc-web natively) or a grpc-web
transcoder in front of an older server. Pyodide ≥ 0.27 recommended; verified on
Pyodide 314.0.4 (CPython 3.14).

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
and POSTs them via `pyodide.http.pyfetch`. Call metadata (API key / OIDC bearer) is
folded into `fetch` headers.

The target is not configurable: under Emscripten the connect helpers
(`use_async_with_local`, `use_async_with_weaviate_cloud`, `use_async_with_custom`) pin
gRPC to the **REST** endpoint — same host, port and TLS — under Weaviate's own
`/v1/grpc-web` base path, so gRPC and REST share one origin and no proxy is needed. That
is deliberate: native gRPC cannot work under WASM at all, so grpc-web on the REST
listener is not a choice that could be wrong. The TypeScript `@weaviate/web` client makes
the same call, dropping `grpcHost`/`grpcPort`/`grpcSecure` from its options entirely.

A grpc-web transcoder on a separate endpoint (Envoy,
[connectrpc/vanguard](https://github.com/connectrpc/vanguard-go)) is therefore not
reachable through the helpers. If you need one — e.g. in front of a Weaviate older than
1.38.3 — build the connection parameters yourself:

```python
from weaviate import WeaviateAsyncClient
from weaviate.connect import ConnectionParams

client = WeaviateAsyncClient(
    ConnectionParams.from_params(
        http_host="weaviate.example.com", http_port=443, http_secure=True,
        grpc_host="transcoder.example.com", grpc_port=443, grpc_secure=True,
        # add grpc_path_prefix="/base/path" if the transcoder is not at the root
    )
)
```

For REST (`is_ready`, collection config, `/batch/references`, …) the package patches
`httpx.AsyncHTTPTransport` with its own `pyfetch`-based transport. It does so even on
Pyodide builds whose bundled httpx has a JS-fetch transport of its own: that transport
cannot read the null body of HEAD requests and 204 responses (`data.exists`,
`data.delete_by_id`, `tenants.exists`, …) and does not enforce the client's per-request
timeouts.

## Usage

With this package installed, a plain `import weaviate` is all you need — under
Emscripten the base client imports `weaviate_client_web` itself before anything else,
which installs the shim and the fetch transport (and raises a clear error if the package
is missing). Against Weaviate ≥ 1.38.3:

```python
import weaviate  # bootstraps weaviate_client_web automatically under Emscripten

client = weaviate.use_async_with_local(port=8080)
await client.connect()       # runs the gRPC health check over grpc-web
collection = client.collections.get("Article")
await collection.query.near_text("hello", limit=3)
```

Nothing selects grpc-web: `use_async_with_local()`, `use_async_with_weaviate_cloud()` and
`use_async_with_custom()` all route gRPC onto the REST endpoint under `/v1/grpc-web` when
they run under Emscripten, and behave exactly as before everywhere else.

```python
client = weaviate.use_async_with_weaviate_cloud(
    cluster_url="rAnD0mD1g1t5.something.weaviate.cloud",
    auth_credentials=weaviate.classes.init.Auth.api_key("my-api-key"),
)
```

`use_async_with_custom()` still requires `grpc_host`/`grpc_port`/`grpc_secure` — Python
cannot drop required parameters on one platform the way TypeScript drops them from a
type. Pass the HTTP values; anything else is overridden with them and warned about
(`Con006`), so a browser client never silently points somewhere it cannot reach.

```python
client = weaviate.use_async_with_custom(
    http_host="localhost", http_port=8080, http_secure=False,
    grpc_host="localhost", grpc_port=8080, grpc_secure=False,   # = the HTTP endpoint
)
```

Pass `headers={...}` / `auth_credentials=...` as usual for API keys, OIDC or WCD.

Importing the companion explicitly first also works and remains the explicit form:

```python
import weaviate_client_web   # installs the grpc shim under Emscripten (no-op elsewhere)
import weaviate
```

## Supported / unsupported

| Feature                                                   | Kind            | Status |
|----------------------------------------------------------|-----------------|--------|
| Search, Aggregate, TenantsGet, BatchObjects, BatchDelete | unary gRPC      | ✅ works over grpc-web |
| Health check (`/grpc.health.v1.Health/Check`)            | unary gRPC      | ✅ runs on `connect()` over grpc-web |
| REST (`is_ready`, config, `/batch/references`, …)         | REST            | ✅ via the package's own fetch transport |
| API-key auth (`Auth.api_key`)                             | header          | ✅ |
| OIDC auth (`client_credentials` / `client_password` / `bearer_token`) | REST | ✅ token fetch + asyncio-task refresh (no threads) |
| Bulk insert: `collection.data.insert_many()`              | unary gRPC      | ✅ the supported bulk path under WASM |
| `batch.stream()` / `batch.experimental()` (BatchStream)  | bidi streaming  | ❌ not possible over grpc-web/fetch — raises immediately; use `insert_many()` |
| `batch.dynamic()` / `fixed_size()` / `rate_limit()`      | sync-client API | ❌ these only exist on the sync client, which is unsupported under WASM |
| Embedded Weaviate (`use_async_with_embedded`)            | subprocess      | ❌ raises "not supported under WebAssembly/Pyodide" |
| Synchronous client                                       | —               | ❌ async-only under WASM |
| Weaviate Agents: `AsyncQueryAgent` `run/ask/search`      | REST            | ✅ via fetch |
| Weaviate Agents: `ask_stream` / `research_stream` (SSE)  | REST streaming  | ⚠️ degraded: the fetch transport buffers the whole response, so events arrive only when the run completes (and long runs can hit the request timeout) |
| Weaviate Agents: sync `QueryAgent`, `TransformationAgent`, `PersonalizationAgent` | REST sync | ❌ no async flavour exists |

## Configuration not honored in the browser

`fetch` manages connections itself, so several knobs are accepted but have no effect
under WASM:

- `AdditionalConfig.proxies` / `trust_env` proxy environment variables (the browser
  cannot proxy fetch requests per-client),
- connection-pool sizing and `session_pool_max_retries`,
- `GrpcConfig.credentials` (custom CA bundles — the browser's trust store decides TLS),
- `GrpcConfig.channel_options`, including `grpc.max_send_message_length` /
  `grpc.max_receive_message_length` (only `grpc-web.path_prefix` is consumed). The
  practical message-size ceiling is the server's `grpcMaxMessageSize` (reported by
  `/v1/meta`); exceeding it surfaces as `RESOURCE_EXHAUSTED`,
- `Proxies.grpc` / `GRPC_PROXY`.

## CORS requirements (browsers)

Weaviate ≥ 1.38.3 serves the CORS headers below for its `/v1/grpc-web` endpoint itself,
with no configuration. Its request-header list is a **closed allowlist**: custom
`headers={...}` that are not on it fail the browser's preflight. Cross-origin
deployments that go through a grpc-web transcoder or a proxy must configure CORS there:

- allow every request header the client sends: `content-type`, `x-grpc-web`,
  `x-user-agent`, `grpc-timeout`, `x-weaviate-client`, `authorization` (when auth is
  used) and `x-weaviate-cluster-url` (Weaviate Cloud);
- expose the grpc-web status headers on responses:
  `Access-Control-Expose-Headers: grpc-status, grpc-message` — without this,
  trailers-only error responses (e.g. a bad API key) are reported as
  `INTERNAL: grpc-web response contained no message frame` instead of the real error;
- note that a CORS-blocked request is indistinguishable from a network failure in the
  browser (`TypeError: Failed to fetch`), and is retried as UNAVAILABLE.

## Testing on CPython

`weaviate_client_web.install(force=True)` installs the shim on a normal CPython
interpreter (run it in a fresh process, before importing `weaviate`). Inject a sender
with `weaviate_client_web.set_sender(...)` (e.g. `make_httpx_sender()`) to exercise the
transport against an Envoy/vanguard transcoder without a browser.
`install_fetch_transport(force=True)` likewise patches httpx on CPython, given an
importable `pyodide.http` stand-in.
