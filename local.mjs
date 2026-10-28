import EmbeddedPostgres from 'embedded-postgres';
import { randomBytes } from 'node:crypto';
import fs from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { spawn } from 'node:child_process';

const root = import.meta.dirname;
const state = resolve(root, '.local');
await fs.mkdir(state, { recursive: true });
const passwordPath = resolve(state, 'database-password');
const password = existsSync(passwordPath) ? (await fs.readFile(passwordPath, 'utf8')).trim() : randomBytes(24).toString('hex');
if (!existsSync(passwordPath)) await fs.writeFile(passwordPath, password);
const databaseDir = resolve(state, 'postgres');
const pg = new EmbeddedPostgres({
  databaseDir, user: 'course', password, port: 55440, persistent: true,
  initdbFlags: ['--encoding=UTF8', '--locale=C'],
  postgresFlags: ['-h', '127.0.0.1', '-c', 'max_connections=20', '-c', 'shared_buffers=16MB'],
  onLog: () => {}, onError: error => process.stderr.write(String(error)),
});
if (!existsSync(resolve(databaseDir, 'PG_VERSION'))) await pg.initialise();
await pg.start();
const python = resolve(root, process.platform === 'win32' ? '.venv/Scripts/python.exe' : '.venv/bin/python');
if (!existsSync(python)) { await pg.stop(); throw new Error('Create .venv and install requirements.txt before npm start'); }
const child = spawn(python, ['webapp.py'], {
  cwd: root, windowsHide: true,
  env: { ...process.env, DATABASE_URL: `postgresql://course:${password}@127.0.0.1:55440/postgres`, PORT: process.env.PORT || '8095', PYTHONIOENCODING: 'utf-8', OPENBLAS_NUM_THREADS: '1', OMP_NUM_THREADS: '1', MKL_NUM_THREADS: '1' },
  stdio: 'inherit',
});
let stopped = false;
async function stop() { if (stopped) return; stopped = true; child.kill(); await pg.stop(); }
process.on('SIGINT', () => stop().then(() => process.exit(0)));
process.on('SIGTERM', () => stop().then(() => process.exit(0)));
child.on('exit', async code => { await stop(); process.exit(code ?? 0); });
