"""Skip collection off Pyodide: these modules import pyodide.

Run them with: node --experimental-wasm-jspi ci/pyodide-e2e/units.mjs dist
"""

import sys

if sys.platform != "emscripten":
    collect_ignore_glob = ["*.py"]
