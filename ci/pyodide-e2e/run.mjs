// Runs e2e.py inside Pyodide under Node against a live Weaviate.
// Usage: node run.mjs <wheels-dir>  (one weaviate_client-*.whl, one weaviate_client_web-*.whl)
// Env: WEAVIATE_HOST (default localhost), WEAVIATE_PORT (default 8090).
// The pyodide npm pin in package.json fixes the interpreter.
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { loadPyodide } from "pyodide";

import { wheelsFromArgv } from "./wheels.mjs";

const { wheelsDir, wheels } = wheelsFromArgv("run.mjs");
const here = dirname(fileURLToPath(import.meta.url));

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
// anyio comes from weaviate-client-web's emscripten marker; installing it here would
// hide a broken marker.

pyodide.FS.mkdirTree("/wheels");
pyodide.mountNodeFS("/wheels", wheelsDir);
for (const wheel of wheels) {
  console.log(`micropip install ${wheel}`);
  await micropip.install(`emfs:/wheels/${wheel}`);
}

// The first import is a bare `import weaviate`: it must install the grpc shim itself.
pyodide.runPython(`
import sys
assert "weaviate_client_web" not in sys.modules
import weaviate
assert getattr(sys.modules.get("grpc"), "__weaviate_client_web_shim__", False), \\
    "bare 'import weaviate' did not install the grpc shim"
print("OK bare 'import weaviate' bootstrapped the grpc shim")
`);

// asyncio.run() is unavailable in Pyodide: load e2e.py, then await main() on Pyodide's loop.
pyodide.runPython(readFileSync(resolve(here, "e2e.py"), "utf8"));
try {
  await pyodide.runPythonAsync("await main()");
} catch (err) {
  console.error(err);
  process.exit(1);
}
// The interpreter keeps live handles on the Node event loop, so exit explicitly.
process.exit(0);
