// Runs the weaviate_client_web unit suite (packages/web/tests) inside Pyodide (WASM)
// under Node, plus bootstrap scenarios that each need a fresh interpreter. No running
// Weaviate is needed — everything is driven through fake senders / a fake pyfetch.
//
// Usage: node units.mjs <wheels-dir>
//   <wheels-dir> must contain exactly the two locally-built pure wheels:
//   weaviate_client-*.whl and weaviate_client_web-*.whl (same layout as run.mjs).
//
// The package imports pyodide at module scope, so this harness is the only place its
// unit tests can run; scenarios needing a clean import state (bootstrap and
// install-hint semantics) get one loadPyodide() each. Deliberately untested: the
// fall-through in weaviate/__init__.py when a real grpc module exists — no grpcio
// wheel exists for Emscripten, so that branch is CPython-only defence and cannot be
// exercised here.
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

// Fresh interpreter with micropip ready and the wheels dir mounted; `only` restricts
// which of the two wheels get installed (the install-hint scenarios need the base
// client without its companion).
async function freshPyodide(only = prefixes) {
  const pyodide = await loadPyodide({});
  await pyodide.loadPackage("micropip");
  const micropip = pyodide.pyimport("micropip");
  pyodide.FS.mkdirTree("/wheels");
  pyodide.mountNodeFS("/wheels", wheelsDir);
  for (const wheel of wheels) {
    if (only.some((p) => wheel.startsWith(p))) {
      await micropip.install(`emfs:/wheels/${wheel}`);
    }
  }
  return pyodide;
}

async function scenario(name, pyodide, code) {
  try {
    pyodide.runPython(code);
    console.log(`OK scenario: ${name}`);
  } catch (err) {
    console.error(`FAIL scenario: ${name}`);
    console.error(err);
    process.exit(1);
  }
}

// --- fresh-interpreter bootstrap scenarios -----------------------------------------

await scenario(
  "bare 'import weaviate' bootstraps the companion",
  await freshPyodide(),
  `
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
`,
);

await scenario(
  "missing companion raises the install hint",
  await freshPyodide(["weaviate_client-"]),
  `
try:
    import weaviate
except ImportError as e:
    assert "weaviate-client-web" in str(e), str(e)
    assert "weaviate-client[grpc-web]" in str(e), str(e)
    assert "WebAssembly/Pyodide" in str(e), str(e)
else:
    raise AssertionError("expected ImportError without the companion")
`,
);

await scenario(
  "a broken companion surfaces its own error, not the install hint",
  await freshPyodide(["weaviate_client-"]),
  `
# An INSTALLED companion whose import fails (here: a missing dependency of its own)
# must raise that error — the "install weaviate-client[grpc-web]" hint would send the
# user to reinstall a package that is already there.
import pathlib, sys
pkg = pathlib.Path("/broken/weaviate_client_web")
pkg.mkdir(parents=True)
(pkg / "__init__.py").write_text(
    "raise ModuleNotFoundError(\\"No module named 'anyio'\\", name='anyio')\\n"
)
sys.path.insert(0, "/broken")
try:
    import weaviate
except ImportError as e:
    assert e.name == "anyio", (e.name, str(e))
    assert "anyio" in str(e), str(e)
    assert "grpc-web" not in str(e), str(e)
else:
    raise AssertionError("expected the companion's own ImportError to surface")
`,
);

// --- the main unit suite -----------------------------------------------------------

const testsDir = resolve(here, "../../packages/web/tests");
const pyodide = await freshPyodide();
console.log(
  `pyodide ${pyodide.version} / python ${pyodide.runPython("import sys; sys.version.split()[0]")}`,
);
pyodide.FS.mkdirTree("/units");
pyodide.mountNodeFS("/units", testsDir);
try {
  await pyodide.runPythonAsync(`
import sys
sys.path.insert(0, "/units")
import runner
await runner.main()
`);
} catch (err) {
  console.error(err);
  process.exit(1);
}
// The interpreters loaded above keep live handles on the Node event loop, so the
// process does not exit on its own.
process.exit(0);
