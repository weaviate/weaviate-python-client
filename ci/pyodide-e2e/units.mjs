// Runs the weaviate_client_web unit suite (packages/web/tests) with pytest inside
// Pyodide (WASM) under Node, plus a bootstrap scenario in a fresh interpreter. No
// running Weaviate is needed — everything is driven through fake senders / a fake
// pyfetch.
//
// Usage: node --experimental-wasm-jspi units.mjs <wheels-dir>
//   <wheels-dir> must contain exactly the two locally-built pure wheels:
//   weaviate_client-*.whl and weaviate_client_web-*.whl (same layout as run.mjs).
//
// The JSPI flag is required: pytest's runner is synchronous, so async tests execute
// through run_until_complete, which needs stack switching (enableRunUntilComplete +
// a callPromising() entrypoint). Without the flag the run fails loudly at startup —
// it can never produce a false green.
//
// The package imports pyodide at module scope, so this harness is the only place its
// unit tests can run. The base client's hook logic (missing companion, broken
// companion, grpc-present fall-through) is covered by subprocess tests in
// test/test_wasm_compat.py on CPython; the bootstrap scenario below covers the one
// path that needs real Pyodide, micropip and the wheels.
import { readdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { loadPyodide } from "pyodide";

if (!process.argv[2]) {
  console.error("usage: node units.mjs <wheels-dir>");
  process.exit(2);
}
const wheelsDir = resolve(process.argv[2]);
const here = dirname(fileURLToPath(import.meta.url));

const wheels = readdirSync(wheelsDir)
  .filter((f) => f.endsWith(".whl"))
  .sort(); // installs weaviate_client before weaviate_client_web, which depends on it
const prefixes = ["weaviate_client-", "weaviate_client_web-"];
if (
  wheels.length !== 2 ||
  !prefixes.every((p) => wheels.some((w) => w.startsWith(p)))
) {
  console.error(
    `expected exactly one weaviate_client-*.whl and one weaviate_client_web-*.whl in ${wheelsDir}, found: ${JSON.stringify(wheels)}`,
  );
  process.exit(2);
}

// Fresh interpreter with micropip ready and the wheels dir mounted.
async function freshPyodide() {
  const pyodide = await loadPyodide({ enableRunUntilComplete: true });
  await pyodide.loadPackage("micropip");
  const micropip = pyodide.pyimport("micropip");
  pyodide.FS.mkdirTree("/wheels");
  pyodide.mountNodeFS("/wheels", wheelsDir);
  for (const wheel of wheels) {
    await micropip.install(`emfs:/wheels/${wheel}`);
  }
  return pyodide;
}

// --- bootstrap scenario: needs a clean import state, so its own interpreter --------

{
  const pyodide = await freshPyodide();
  try {
    pyodide.runPython(`
import sys
assert "weaviate_client_web" not in sys.modules
import weaviate  # the ONLY weaviate-side import: must bootstrap the companion
assert "weaviate_client_web" in sys.modules, "hook did not import the companion"
import weaviate_client_web
import grpc
import httpx
assert weaviate_client_web.is_installed()
assert weaviate_client_web.is_fetch_transport_installed()
assert getattr(grpc, "__weaviate_client_web_shim__", False) is True
assert getattr(
    httpx.AsyncHTTPTransport.handle_async_request, "__weaviate_fetch_shim__", False
) is True
`);
    console.log("OK scenario: bare 'import weaviate' bootstraps the companion");
  } catch (err) {
    console.error("FAIL scenario: bare 'import weaviate' bootstraps the companion");
    console.error(err);
    process.exit(1);
  }
}

// --- the pytest suite --------------------------------------------------------------

const testsDir = resolve(here, "../../packages/web/tests");
const pyodide = await freshPyodide();
console.log(
  `pyodide ${pyodide.version} / python ${pyodide.runPython("import sys; sys.version.split()[0]")}`,
);
const micropip = pyodide.pyimport("micropip");
// A metadata-coherent pair: pytest-asyncio 0.25.3 declares pytest<9,>=8.2. Its
// run_until_complete-based execution stack-switches correctly under JSPI, unlike the
// asyncio.Runner-based pytest-asyncio 1.x, whose async tests fail here. (The Pyodide
// distribution bundles pytest 9 next to pytest-asyncio 0.25.3, contradicting that
// constraint — micropip tolerates it, but there is no reason to depend on its
// leniency, so both are pinned from PyPI.)
await micropip.install(["pytest==8.4.2", "pytest-asyncio==0.25.3"]);
pyodide.FS.mkdirTree("/units");
pyodide.mountNodeFS("/units", testsDir);

// pytest.main is synchronous; entering through callPromising() lets the async tests
// stack-switch (run_until_complete) instead of failing with "Cannot stack switch".
const runPytest = pyodide.runPython(`
import sys
sys.dont_write_bytecode = True  # /units is the host checkout: no __pycache__ in it

import pytest

def _run():
    return int(pytest.main([
        "-v",
        "-p", "no:cacheprovider",  # no .pytest_cache in the host checkout either
        "-o", "asyncio_mode=auto",
        "-o", "asyncio_default_fixture_loop_scope=function",
        "/units",
    ]))

_run
`);
let exitCode;
try {
  exitCode = await runPytest.callPromising();
} catch (err) {
  console.error(err);
  process.exit(1);
}
// Any nonzero pytest exit code fails the run — including 5, "no tests collected".
console.log(`pytest exit code: ${exitCode}`);
// The interpreters loaded above keep live handles on the Node event loop, so the
// process does not exit on its own.
process.exit(exitCode === 0 ? 0 : 1);
