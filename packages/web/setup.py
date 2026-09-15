"""Injects the lockstep ``weaviate-client==<version>`` pin at build time.

Both packages derive their version from the repository's git tags (setuptools_scm), so
the version is only known when the wheel is built and a static ``dependencies`` list
cannot express the pin. The pin makes mismatched pairs unresolvable at install time:
the two packages share private contracts (the ``HTTP <status>`` error-string markers,
the exception constants ``_channel`` imports), so a companion must only ever install
next to the base client it was built with.

Consequence for releasing: every tag must publish BOTH packages — a base-only release
would leave the extra pointing at a companion whose pin no longer resolves.
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
