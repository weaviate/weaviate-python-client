# weaviate-client-web

Runs the async [Weaviate Python client](https://github.com/weaviate/weaviate-python-client)
under Pyodide (browser pages, marimo notebooks, Web Workers): gRPC goes over grpc-web and
REST over `fetch`.

Requires Weaviate ≥ 1.38.3 (the first release serving grpc-web) or a grpc-web transcoder
in front of an older server. Tested on Pyodide 314.0.4 (CPython 3.14).

## Installation

Install through the base client's `grpc-web` extra:

```python
import micropip
await micropip.install("weaviate-client[grpc-web]")
```

The extra has a `sys_platform == "emscripten"` marker, so it installs nothing on CPython.
`micropip.install("weaviate-client-web")` also works; it pins `weaviate-client` to its own
version. Both need a `weaviate-client` release that ships the extra; older releases fail to
resolve `grpcio`.

The package imports `pyodide` at module scope, so it imports only under Pyodide.

## How it works

Under Pyodide there is no `grpcio` wheel. Importing this package puts a pure-Python `grpc`
shim in `sys.modules`, and `GrpcWebChannel` sends unary RPCs as grpc-web POSTs through
`pyodide.http.pyfetch`. Call metadata (API key, OIDC bearer) becomes fetch headers.

Under Pyodide the connect helpers send gRPC to the REST endpoint (same host, port and TLS)
under `/v1/grpc-web`. As in the TypeScript `@weaviate/web` client, native gRPC is not
available there, so this endpoint is not configurable through the helpers.

To use a grpc-web transcoder on another endpoint (Envoy,
[vanguard](https://github.com/connectrpc/vanguard-go)), for example in front of
Weaviate < 1.38.3, build the connection parameters yourself:

```python
from weaviate import WeaviateAsyncClient
from weaviate.connect import ConnectionParams

client = WeaviateAsyncClient(
    ConnectionParams.from_params(
        http_host="weaviate.example.com", http_port=443, http_secure=True,
        grpc_host="transcoder.example.com", grpc_port=443, grpc_secure=True,
        # add grpc_path_prefix="/prefix" if the transcoder is not at the root
    )
)
```

REST goes through the package's own `fetch`-based httpx transport, including on Pyodide
builds whose httpx has one (that one fails on body-less HEAD/204 responses).

## Usage

With this package installed, `import weaviate` imports it first, under Pyodide only. If it
is missing, `import weaviate` raises an ImportError naming the extra. Against
Weaviate ≥ 1.38.3:

```python
import weaviate

client = weaviate.use_async_with_local(port=8080)
await client.connect()       # runs the gRPC health check over grpc-web
collection = client.collections.get("Article")
await collection.query.near_text("hello", limit=3)
```

```python
client = weaviate.use_async_with_weaviate_cloud(
    cluster_url="rAnD0mD1g1t5.something.weaviate.cloud",
    auth_credentials=weaviate.classes.init.Auth.api_key("my-api-key"),
)
```

Weaviate Cloud: browser use requires **Allow all CORS origins** in the cluster's settings
in the Weaviate Cloud console (takes a few minutes to apply). Until it applies, the client
fails at its first REST call with a `Failed to fetch` connection error.

`use_async_with_custom()` still requires `grpc_host`/`grpc_port`/`grpc_secure`. Under
Pyodide they are ignored: gRPC always uses the REST endpoint, and values that differ from
the HTTP ones are reported in a `Con006` warning. Code that also runs on CPython should
keep its native gRPC values (there, the same host and port for both is an error) and may
ignore that warning.

```python
client = weaviate.use_async_with_custom(
    http_host="localhost", http_port=8080, http_secure=False,
    grpc_host="localhost", grpc_port=50051, grpc_secure=False,  # CPython; ignored under Pyodide
)
```

Pass `headers={...}` / `auth_credentials=...` as usual for API keys, OIDC or Weaviate Cloud.
Importing `weaviate_client_web` before `weaviate` is equivalent.

## Supported / unsupported

| Feature                                                   | Kind            | Status |
|----------------------------------------------------------|-----------------|--------|
| Search, Aggregate, TenantsGet, BatchObjects, BatchDelete | unary gRPC      | Yes, over grpc-web |
| Health check (`/grpc.health.v1.Health/Check`)            | unary gRPC      | Yes, on `connect()` over grpc-web |
| REST (`is_ready`, config, `/batch/references`, …)         | REST            | Yes, via the package's own fetch transport |
| API-key auth (`Auth.api_key`)                             | header          | Yes |
| OIDC auth (`client_credentials` / `client_password` / `bearer_token`) | REST | Untested: token refresh runs on an asyncio task (no threads) |
| Bulk insert: `collection.data.insert_many()`              | unary gRPC      | Yes, the bulk path under Pyodide |
| `batch.stream()` / `batch.experimental()` (BatchStream)  | bidi streaming  | No: grpc-web has no bidirectional streaming; raises at once, use `insert_many()` |
| `batch.dynamic()` / `fixed_size()` / `rate_limit()`      | sync-client API | No: sync client only |
| Embedded Weaviate (`use_async_with_embedded`)            | subprocess      | No: raises "not supported under Pyodide" |
| Synchronous client                                       | —               | No: async only |

## Configuration not honored in the browser

`fetch` manages connections itself, so several knobs are accepted but have no effect
under Pyodide:

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

Self-hosted Weaviate ≥ 1.38.3 (unchanged through 1.40.0-rc.1) answers CORS for its
`/v1/grpc-web` endpoint as follows (for Weaviate Cloud, see [Usage](#usage)):

- allowed origins come from `CORS_ALLOW_ORIGIN` (default `*`);
- allowed request headers are `X-Grpc-Web`, `X-User-Agent`, `Grpc-Timeout`,
  `Connect-Protocol-Version`, `Connect-Timeout-Ms` and `X-Weaviate-Client`, plus everything
  in `CORS_ALLOW_HEADERS`, whose default already covers `Content-Type`, `Authorization`,
  `X-Weaviate-Cluster-Url` and the vendor `*-Api-Key` headers;
- exposed response headers are `Grpc-Status`, `Grpc-Message` and
  `Grpc-Status-Details-Bin`.

A custom `headers={...}` entry outside that list must be added to `CORS_ALLOW_HEADERS`,
or the browser's preflight rejects the request. A proxy or grpc-web transcoder in front of
Weaviate must allow the same origins and request headers and expose the same response
headers; without `grpc-status, grpc-message` exposed, trailers-only error responses (e.g.
a bad API key) are reported as `INTERNAL: grpc-web response contained no message frame`
instead of the real error.

In the browser a CORS-blocked request is indistinguishable from a network failure
(`TypeError: Failed to fetch`); the error text names CORS as one possible cause. On a
channel that has not yet received any response such a failure is reported as `UNKNOWN`
and fails at once; after the first response it is `UNAVAILABLE` and retried.

## Testing

Because the package imports `pyodide` at module scope, its unit tests run inside
Pyodide. From the repository root:

```sh
python -m build --wheel --outdir dist .
python -m build --wheel --outdir dist packages/web
npm install --prefix ci/pyodide-e2e
node --experimental-wasm-jspi ci/pyodide-e2e/units.mjs dist   # pytest unit suite, no Weaviate needed
node ci/pyodide-e2e/run.mjs dist                              # e2e suite, needs a running Weaviate (see ci/)
```
