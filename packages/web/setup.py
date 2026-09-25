"""Pins weaviate-client==<this version> at build time (the version comes from git tags).

The packages share private contracts (the "HTTP <status>" details that weaviate.exceptions
matches, and the grpc-web constants _channel imports from weaviate.connect.base), so every
release tag must publish both.
"""

from setuptools import setup
from setuptools_scm import get_version

version = get_version(root="../..", relative_to=__file__)

setup(
    install_requires=[
        f"weaviate-client=={version}",
        # Pyodide's bundled httpx build omits anyio, but authlib imports it directly.
        'anyio ; sys_platform == "emscripten"',
    ]
)
