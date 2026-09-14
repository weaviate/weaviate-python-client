"""Collects and runs the test modules in this directory on Pyodide's event loop.

Invoked by ``ci/pyodide-e2e/units.mjs``, which mounts this directory into the
interpreter and awaits :func:`main` (``asyncio.run()`` cannot be used inside Pyodide).
Test functions are ``test_*`` callables — plain or ``async`` — collected per module,
so names are qualified and cannot shadow across files.
"""

import inspect
import traceback
from typing import List

import test_framing
import test_httpx_fetch
import test_shim_install
import test_transport

_MODULES = (test_framing, test_transport, test_httpx_fetch, test_shim_install)


async def main() -> None:
    tests = []
    for module in _MODULES:
        for name in sorted(vars(module)):
            fn = getattr(module, name)
            if name.startswith("test_") and callable(fn):
                tests.append((f"{module.__name__}.{name}", fn))
    failures: List[str] = []
    for name, fn in tests:
        try:
            result = fn()
            if inspect.iscoroutine(result):
                await result
        except Exception:
            failures.append(name)
            traceback.print_exc()
            print(f"FAIL {name}", flush=True)
        else:
            print(f"OK {name}", flush=True)
    print(f"{len(tests) - len(failures)}/{len(tests)} unit tests passed", flush=True)
    if failures:
        raise SystemExit(f"{len(failures)} unit test(s) failed: {', '.join(failures)}")
