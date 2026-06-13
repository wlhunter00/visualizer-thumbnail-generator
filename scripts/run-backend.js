import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const rootDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const backendDir = path.join(rootDir, 'backend');
const python =
  process.platform === 'win32'
    ? path.join(backendDir, '.venv', 'Scripts', 'python.exe')
    : path.join(backendDir, '.venv', 'bin', 'python');

if (!existsSync(python)) {
  console.error(
    'Backend virtual environment not found.\n' +
      'Run: cd backend && python -m venv .venv && pip install -r requirements.txt'
  );
  process.exit(1);
}

const child = spawn(python, ['main.py'], {
  cwd: backendDir,
  stdio: 'inherit',
  shell: process.platform === 'win32',
});

child.on('exit', (code) => process.exit(code ?? 1));
