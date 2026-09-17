"""Restrict this suite to Pyodide.

The package under test imports ``pyodide`` at module scope, so the test modules here
are only importable under Emscripten/Pyodide. There, pytest runs them via
``ci/pyodide-e2e/units.mjs`` (async tests execute on Pyodide's event loop through JSPI
stack switching). On CPython, keep pytest from collecting them:

    node --experimental-wasm-jspi ci/pyodide-e2e/units.mjs dist
"""

import sys

if sys.platform != "emscripten":
    collect_ignore_glob = ["*.py"]
