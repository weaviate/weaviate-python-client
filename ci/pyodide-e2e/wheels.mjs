// Shared by run.mjs and units.mjs: resolves <wheels-dir> (argv[2]) to exactly the two
// locally-built pure wheels, weaviate_client-*.whl and weaviate_client_web-*.whl.
import { readdirSync } from "node:fs";
import { resolve } from "node:path";

export function wheelsFromArgv(script) {
  if (!process.argv[2]) {
    console.error(`usage: node ${script} <wheels-dir>`);
    process.exit(2);
  }
  const wheelsDir = resolve(process.argv[2]);
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
  return { wheelsDir, wheels };
}
