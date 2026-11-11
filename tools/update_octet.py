"""Stage an Octet update with a three-way merge; never change the live snapshot.

Requires a local upstream Git clone containing both revisions. After reviewing
conflicts and testing the staged tree, copy it into frontend/octet and rebuild.
"""
import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def stage_update(upstream, ref, output, local=None):
    local = Path(local or ROOT / 'frontend/octet').resolve()
    upstream, output = Path(upstream).resolve(), Path(output).resolve()
    if output == local or local in output.parents or output.exists():
        raise ValueError('Choose a new staging directory outside frontend/octet')

    def git(*args):
        return subprocess.check_output(['git', '-C', str(upstream), *args])

    notes = (local / 'UPSTREAM.md').read_text()
    base = re.search(r'^Commit: ([0-9a-f]{40})\.', notes, re.M).group(1)
    target = git('rev-parse', '--verify', ref + '^{commit}').decode().strip()
    # -z: without it git quotes non-ASCII names and such files would be skipped.
    old_names = set(filter(None, git('ls-tree', '-r', '-z', '--name-only', base).decode().split('\0')))
    new_names = set(filter(None, git('ls-tree', '-r', '-z', '--name-only', target).decode().split('\0')))
    local_names = {p.relative_to(local).as_posix() for p in local.rglob('*')
                   if p.is_file() and not ({'node_modules', '.git'} & set(p.relative_to(local).parts))}
    # Preserve the existing vendoring boundary: drawing sources/assets/checks,
    # no Tauri application, CI workflows or release tooling at the repository root.
    roots = {p.split('/')[0] for p in local_names if '/' in p} - {'src-tauri'}
    candidates = local_names | {p for p in new_names - old_names if p.split('/')[0] in roots}
    report = dict(base=base, target=target, updated=[], merged=[], conflicts=[], removed=[])
    output.mkdir(parents=True)
    for name in sorted(candidates):
        ours = (local / name).read_bytes() if name in local_names else None
        old = git('show', base + ':' + name) if name in old_names else None
        new = git('show', target + ':' + name) if name in new_names else None
        if old == new:
            result = ours
        elif ours == old or ours == new:
            result = new
            report['updated'].append(name)
        elif old is None or ours is None or new is None:
            result = ours if ours is not None else new
            report['conflicts'].append(name)
        elif b'\x00' in ours + old + new:
            result = ours
            report['conflicts'].append(name)
        else:
            with tempfile.TemporaryDirectory(prefix='octet-merge-') as d:
                files = [Path(d) / part for part in ('local', 'base', 'upstream')]
                for p, data in zip(files, (ours, old, new)):
                    p.write_bytes(data)
                merged = subprocess.run(['git', 'merge-file', '-p', '-L', 'Elucida', '-L', base[:12],
                                         '-L', target[:12], *map(str, files)], capture_output=True)
                if merged.returncode < 0 or merged.returncode > 127:
                    raise RuntimeError(merged.stderr.decode(errors='replace'))
                result = merged.stdout
                report['conflicts' if merged.returncode else 'merged'].append(name)
        if result is None:
            report['removed'].append(name)
        else:
            dest = output / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(result)
    # The target provenance is explicit even when conflicts still need review.
    (output / 'UPSTREAM.md').write_text(notes.replace('Commit: ' + base + '.', 'Commit: ' + target + '.'))
    report_path = output.with_name(output.name + '-merge.json')
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    return report, report_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upstream', required=True, type=Path)
    parser.add_argument('--ref', required=True, help='Reviewed upstream commit or release tag')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    report, path = stage_update(args.upstream, args.ref, args.output)
    print(json.dumps(report, indent=2))
    print('Review report:', path)
    raise SystemExit(bool(report['conflicts']))
