import { spawn } from 'node:child_process';

const workspace = process.env.ARC_WORKSPACE_PATH || process.cwd();
const child = spawn('theia', ['start', '--port', '3000', '--hostname', '127.0.0.1', '--root-dir', workspace], {
  stdio: 'inherit',
  env: { ...process.env, ARC_WORKSPACE_PATH: workspace },
  shell: process.platform === 'win32',
});

child.on('exit', code => process.exit(code ?? 0));
