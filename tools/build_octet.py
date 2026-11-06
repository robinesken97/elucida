"""Reproducible frontend build; requires Node/npm and the checked-in package-lock.json."""
import shutil
import subprocess
from pathlib import Path
root = Path(__file__).resolve().parent.parent
npm = shutil.which('npm')
if not npm:
    raise SystemExit('Install Node.js (tested: 24.22.1), including npm, first.')
folder = root / 'frontend/octet'
subprocess.run([npm, 'ci'], cwd=folder, check=True)
subprocess.run([npm, 'run', 'build:embed'], cwd=folder, check=True)
for name in ('LICENSE', 'THIRD_PARTY.md', 'UPSTREAM.md'):
    shutil.copy2(folder / name, root / 'assets/octet' / name)
shutil.copytree(folder / 'licenses', root / 'assets/octet/licenses', dirs_exist_ok=True)
