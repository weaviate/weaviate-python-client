// Runs the Weaviate Python client e2e suite (e2e.py) inside Pyodide (WASM) under Node.
//
// Usage: node run.mjs <wheels-dir>
//   <wheels-dir> must contain exactly the two locally-built pure wheels:
//   weaviate_client-*.whl and weaviate_client_web-*.whl.
// Env: WEAVIATE_HOST (default localhost), WEAVIATE_PORT (default 8090).
//
// The pinned `pyodide` npm package fixes the interpreter (the 314.x line bundles
// CPython 3.14), so there is no Python version matrix here. micropip installs the two
// local wheels; transitive deps resolve from the Pyodide distribution
// (pydantic/pydantic_core/cryptography ship wasm builds there — pydantic_core has no
// wasm wheel on PyPI) or from PyPI as pure wheels (protobuf), and the base client's
// `grpcio; sys_platform != "emscripten"` marker correctly skips grpcio.
import { readdirSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { loadPyodide } from "pyodide";

if (!process.argv[2]) {
  console.error("usage: node run.mjs <wheels-dir>");
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

const pyodide = await loadPyodide({
  env: {
    WEAVIATE_HOST: process.env.WEAVIATE_HOST ?? "localhost",
    WEAVIATE_PORT: process.env.WEAVIATE_PORT ?? "8090",
  },
});
console.log(
  `pyodide ${pyodide.version} / python ${pyodide.runPython("import sys; sys.version.split()[0]")}`,
);

await pyodide.loadPackage("micropip");
const micropip = pyodide.pyimport("micropip");
// anyio (needed because Pyodide's httpx recipe drops it, while authlib imports it
// directly) resolves from the companion wheel's `anyio ; sys_platform == "emscripten"`
// marker — no explicit install here, so the marker stays proven.

pyodide.FS.mkdirTree("/wheels");
pyodide.mountNodeFS("/wheels", wheelsDir);
for (const wheel of wheels) {
  console.log(`micropip install ${wheel}`);
  await micropip.install(`emfs:/wheels/${wheel}`);
}

// Single-import check: the FIRST weaviate-side import in this interpreter is a bare
// `import weaviate` — the base client must bootstrap the companion (and the shim) itself.
pyodide.runPython(`
import sys
assert "weaviate_client_web" not in sys.modules
import weaviate
assert getattr(sys.modules.get("grpc"), "__weaviate_client_web_shim__", False), \\
    "bare 'import weaviate' did not install the grpc shim"
print("OK bare 'import weaviate' bootstrapped the grpc shim")
`);

// Define e2e.py's globals (imports run here, installing the grpc shim), then await
// main() on Pyodide's event loop — asyncio.run() cannot be used inside Pyodide.
pyodide.runPython(readFileSync(resolve(here, "e2e.py"), "utf8"));
try {
  await pyodide.runPythonAsync("await main()");
} catch (err) {
  console.error(err);
  process.exit(1);
}
