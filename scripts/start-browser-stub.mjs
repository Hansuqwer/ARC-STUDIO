import { spawn } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const repoRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const workspace = process.env.ARC_WORKSPACE_PATH || repoRoot;
const stub = process.env.ARC_SWARMGRAPH_CLI || join(repoRoot, 'tests', 'e2e', 'fixtures', 'swarmgraph-stub.sh');

console.warn('Starting ARC Studio with the test SwarmGraph stub. Do not use for release validation.');
const child = spawn('theia', ['start', '--port', '3000', '--hostname', '127.0.0.1', '--root-dir', workspace], {
  stdio: 'inherit',
  env: { ...process.env, ARC_WORKSPACE_PATH: workspace, ARC_SWARMGRAPH_CLI: stub, ARC_SWARMGRAPH_RUN_BACKEND: 'stub' },
  shell: process.platform === 'win32',
});

child.on('exit', code => process.exit(code ?? 0));
