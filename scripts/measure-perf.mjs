#!/usr/bin/env node
import { performance } from "node:perf_hooks";
import { execSync } from "node:child_process";

const kind = process.argv[2];
if (!["build", "pytest"].includes(kind)) {
  console.error("usage: measure-perf.mjs <build|pytest>");
  process.exit(2);
}

const cmd = {
  build:  ["pnpm", "--filter", "arc-extension", "build"],
  pytest: ["uv", "run", "--directory", "python", "pytest", "-q"],
}[kind];

const t0 = performance.now();
try {
  execSync(cmd.join(" "), { stdio: "inherit" });
} catch (err) {
  console.error(JSON.stringify({ kind, ok: false, ms: performance.now() - t0, ts: Date.now() }));
  process.exit(1);
}
console.log(JSON.stringify({ kind, ok: true, ms: performance.now() - t0, ts: Date.now() }));
