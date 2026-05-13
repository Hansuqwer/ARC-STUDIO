import { spawn } from 'node:child_process';
import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const repoRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const workspace = process.env.ARC_WORKSPACE_PATH || repoRoot;

console.warn('[arc] Starting with real ARC backend');

// Explicit allow-list; do NOT spread process.env
const env = {
  PATH: process.env.PATH,
  HOME: process.env.HOME,
  USER: process.env.USER,
  LANG: process.env.LANG ?? 'C.UTF-8',
  ARC_WORKSPACE_PATH: workspace
  // Add other ARC_* vars as needed, but explicitly
};

const child = spawn(
  'theia',
  ['start', '--port', '3000', '--hostname', '127.0.0.1', '--root-dir', workspace],
  { env, stdio: 'inherit', shell: process.platform === 'win32' }
);
child.on('exit', code => process.exit(code ?? 1));
