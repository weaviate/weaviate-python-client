# Weaviate Python Client

<img src="https://weaviate.io/img/site/weaviate-logo-light.png" alt="Weaviate logo" width="180" align="right">

[![PyPI version](https://img.shields.io/pypi/v/weaviate-client)](https://pypi.org/project/weaviate-client/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://pypi.org/project/weaviate-client/)
[![CI](https://github.com/weaviate/weaviate-python-client/actions/workflows/main.yaml/badge.svg?branch=main)](https://github.com/weaviate/weaviate-python-client/actions/workflows/main.yaml)
[![Documentation Status](https://app.readthedocs.org/projects/weaviate-python-client/badge/?version=latest)](https://weaviate-python-client.readthedocs.io/en/latest/)
[![License](https://img.shields.io/badge/license-BSD--3--Clause-blue)](https://github.com/weaviate/weaviate-python-client/blob/main/LICENSE)

The official Python client for [Weaviate](https://weaviate.io).
It has a sync client, `WeaviateClient`, and an async client, `WeaviateAsyncClient`.
Data and query calls go over gRPC. Everything else goes over REST.
The client is fully typed and needs Python 3.10 or newer.

## Installation

```bash
pip install -U weaviate-client
```

Or with uv:

```bash
uv add weaviate-client
```

Optional extras:

- `weaviate-client[agents]` installs the [Weaviate Agents](https://github.com/weaviate/weaviate-agents-python-client) client.
- `weaviate-client[grpc-web]` runs the async client in Pyodide and WebAssembly. It is a no-op on CPython.

## Quickstart

This example connects to Weaviate Cloud and uses Weaviate Embeddings, so you need no third-party API key.

```python
import os

import weaviate
from weaviate.classes.config import Configure
from weaviate.classes.init import Auth

with weaviate.connect_to_weaviate_cloud(
    cluster_url=os.environ["WEAVIATE_URL"],
    auth_credentials=Auth.api_key(os.environ["WEAVIATE_API_KEY"]),
) as client:
    movies = client.collections.create(
        name="Movie",
        vector_config=Configure.Vectors.text2vec_weaviate(),
    )

    movies.data.insert_many([
        {"title": "The Matrix", "genre": "Science Fiction"},
        {"title": "Spirited Away", "genre": "Animation"},
        {"title": "The Lord of the Rings", "genre": "Fantasy"},
    ])

    response = movies.query.near_text(query="sci-fi", limit=2)
    for obj in response.objects:
        print(obj.properties)
```

For a local Docker instance, use `weaviate.connect_to_local()` instead.
See the [quickstart](https://docs.weaviate.io/weaviate/quickstart) for a full walkthrough.

## Async

Use `WeaviateAsyncClient` in async code. The `use_async_with_*` helpers create one.

```python
import weaviate

async with weaviate.use_async_with_local() as client:
    movies = client.collections.use("Movie")
    response = await movies.query.near_text(query="sci-fi", limit=2)
```

See the [async client docs](https://docs.weaviate.io/weaviate/client-libraries/python/async).

## Embedded Weaviate

Embedded Weaviate starts a Weaviate server from your Python process. It runs on Linux and macOS.

```python
import weaviate

with weaviate.connect_to_embedded() as client:
    print(client.is_ready())
```

See [Embedded Weaviate](https://docs.weaviate.io/deploy/installation-guides/embedded).

## Browser and Pyodide

The `grpc-web` extra runs the async client under Pyodide, for example in a browser or a marimo notebook.
gRPC calls go over grpc-web and REST calls go over `fetch`.
The sync client, `batch.stream()` and Embedded Weaviate do not work there.
It needs Weaviate 1.38.3 or newer.
See the [grpc-web package README](https://github.com/weaviate/weaviate-python-client/blob/main/packages/web/README.md).

## Compatibility

This client supports Weaviate 1.32.0 and newer. The 4.x client is actively supported. The 3.x client is deprecated.
For which client version matches which server version, see the [release notes](https://docs.weaviate.io/weaviate/release-notes).

The client checks the server version when it connects and raises an error if the server is too old.

## Documentation

- [Python client docs](https://docs.weaviate.io/weaviate/client-libraries/python)
- [Quickstart](https://docs.weaviate.io/weaviate/quickstart)
- [API reference](https://weaviate-python-client.readthedocs.io)
- [Changelog](https://github.com/weaviate/weaviate-python-client/blob/main/docs/changelog.rst) and [GitHub releases](https://github.com/weaviate/weaviate-python-client/releases)
- [Migrating from v3 to v4](https://archive.docs.weaviate.io/weaviate/client-libraries/python/v3_v4_migration)

## Support

- Ask questions on the [Weaviate forum](https://forum.weaviate.io).
- Report bugs in [GitHub issues](https://github.com/weaviate/weaviate-python-client/issues).
- Report security vulnerabilities privately through the [Weaviate security report page](https://weaviate.io/security-report). Do not open a public issue.

## Contributing

Contributions are welcome.
Read [CONTRIBUTING.md](https://github.com/weaviate/weaviate-python-client/blob/main/CONTRIBUTING.md) before you open a pull request.

## License

BSD 3-Clause. See [LICENSE](https://github.com/weaviate/weaviate-python-client/blob/main/LICENSE).
