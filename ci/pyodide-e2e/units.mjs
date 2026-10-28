// Runs packages/web/tests with pytest inside Pyodide under Node, plus a fresh-interpreter
// bootstrap check. No Weaviate needed.
// Usage: node --experimental-wasm-jspi units.mjs <wheels-dir>  (same wheels as run.mjs)
// JSPI is required: pytest runs async tests through run_until_complete (stack switching).
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { loadPyodide } from "pyodide";

import { wheelsFromArgv } from "./wheels.mjs";

const { wheelsDir, wheels } = wheelsFromArgv("units.mjs");
const here = dirname(fileURLToPath(import.meta.url));

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
import weaviate  # first weaviate import: installs weaviate_client_web
assert "weaviate_client_web" in sys.modules, "hook did not import weaviate_client_web"
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
    console.log("OK scenario: bare 'import weaviate' bootstraps weaviate_client_web");
  } catch (err) {
    console.error("FAIL scenario: bare 'import weaviate' bootstraps weaviate_client_web");
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
// pytest-asyncio 1.x (asyncio.Runner) fails under JSPI; 0.25.3 needs pytest<9, so pin
// both from PyPI.
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
