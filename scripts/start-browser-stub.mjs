import { spawn } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const repoRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const workspace = process.env.ARC_WORKSPACE_PATH || repoRoot;
const stubCli = process.env.ARC_SWARMGRAPH_CLI ||
                join(repoRoot, 'packages/arc-test-fixtures/bin/swarmgraph-stub.mjs');

console.warn('[arc] STUB backend — for tests only, no real agents will run.');

// Explicit allow-list; do NOT spread process.env
const env = {
  PATH: process.env.PATH,
  HOME: process.env.HOME,
  USER: process.env.USER,
  LANG: process.env.LANG ?? 'C.UTF-8',
  ARC_WORKSPACE_PATH: workspace,
  ARC_SWARMGRAPH_CLI: stubCli,
  ARC_SWARMGRAPH_RUN_BACKEND: 'stub'
  // ARC_SWARMGRAPH_ALLOW_COSTS deliberately UNSET
};

const child = spawn(
  'theia',
  ['start', '--port', '3000', '--hostname', '127.0.0.1', '--root-dir', workspace],
  { env, stdio: 'inherit', shell: process.platform === 'win32' }
);
child.on('exit', code => process.exit(code ?? 1));
