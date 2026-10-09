// Runs e2e.py inside Pyodide under Node against a live Weaviate.
// Usage: node run.mjs <wheels-dir>  (one weaviate_client-*.whl, one weaviate_client_web-*.whl)
// Env: WEAVIATE_HOST (default localhost), WEAVIATE_PORT (default 8090).
// The pyodide npm pin in package.json fixes the interpreter.
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
