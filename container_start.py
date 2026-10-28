import os
from pathlib import Path
import subprocess
import sys

os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')


def main():
    binary = Path('/usr/lib/postgresql/15/bin')
    data = Path('/tmp/ilearning-postgres')
    if not (data / 'PG_VERSION').exists():
        subprocess.run([str(binary / 'initdb'), '-D', str(data), '-A', 'trust', '--no-locale', '-E', 'UTF8'], check=True)
    subprocess.run([
        str(binary / 'pg_ctl'), '-D', str(data), '-l', '/tmp/ilearning-postgres.log',
        '-o', '-h 127.0.0.1 -p 5432 -c max_connections=20 -c shared_buffers=16MB', '-w', 'start',
    ], check=True)
    os.environ['DATABASE_URL'] = 'postgresql://postgres@127.0.0.1:5432/postgres'
    from task6.setup_database import setup
    setup(os.environ['DATABASE_URL'])
    try:
        subprocess.run([
            sys.executable, '-m', 'gunicorn', '--bind', '0.0.0.0:' + os.environ.get('PORT', '10000'),
            '--workers', '1', '--threads', '4', '--timeout', '120', 'webapp:app',
        ], check=True)
    finally:
        subprocess.run([str(binary / 'pg_ctl'), '-D', str(data), '-m', 'fast', '-w', 'stop'], check=False)


if __name__ == '__main__':
    main()
