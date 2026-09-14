"""Keep pytest away from this directory.

The package under test imports ``pyodide`` at module scope, so the test modules here
are only importable under Emscripten/Pyodide. They are run by
``ci/pyodide-e2e/units.mjs`` (via ``runner.py``), not by pytest.
"""

collect_ignore_glob = ["*.py"]
