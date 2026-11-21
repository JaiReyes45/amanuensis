#!/usr/bin/env python3
"""Bounded, dependency-free project inventory and documentation checkpoints.

Python 3.11+. Never executes project code or contacts a remote service.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
from fnmatch import fnmatchcase
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tomllib
from urllib.parse import unquote, urlsplit

SECTIONS = (
    'Overview', 'Architecture', 'Repository map', 'Setup and configuration',
    'Operation and deployment', 'Features and workflows', 'Visual walkthrough',
    'Demo', 'User handoff', 'Developer handoff', 'Troubleshooting and limitations',
    'Evidence and freshness',
)
SKIP_DIRS = {'.git', '.hg', '.svn', 'node_modules', '.venv', 'venv', '__pycache__',
             '.pytest_cache', '.mypy_cache', '.next', '.nuxt', 'dist', 'build',
             'coverage', 'vendor', 'target', '.amanuensis', '.aws', '.ssh'}
SECRET_NAMES = {'credentials', 'credentials.json', 'secrets.json', 'secrets.yaml',
                'secrets.yml', 'id_rsa', 'id_ed25519', '.npmrc', '.pypirc'}
SECRET_SUFFIXES = {'.pem', '.key', '.p12', '.pfx', '.keystore'}
TEMPLATES = {'.env.example', '.env.sample', '.env.template'}
LOCKFILES = {'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', 'uv.lock',
             'poetry.lock', 'Cargo.lock', 'Pipfile.lock', 'bun.lock', 'bun.lockb'}


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def linked(path):
    """Reparse points include Windows junctions, including on Python 3.11."""
    return path.is_symlink() or bool(getattr(path.lstat(), 'st_file_attributes', 0)
                                    & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def load(path, default=None):
    if path.is_symlink():
        raise ValueError('Refusing linked state file: ' + path.name)
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding='utf-8'))


def safe_path(root, relative):
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError(f'Path outside project: {relative}')
    return candidate


def state_dir(root):
    directory = safe_path(root, '.amanuensis')
    if directory.is_symlink() or (root / '.amanuensis').is_symlink():
        raise ValueError('State directory must not be a symlink')
    return directory


def save(root, name, data):
    directory = state_dir(root)
    directory.mkdir(exist_ok=True)
    path = safe_path(root, '.amanuensis/' + name)
    if (directory / name).is_symlink():
        raise ValueError('State file must not be a symlink')
    temporary = path.with_suffix('.tmp')
    if temporary.is_symlink():
        raise ValueError('Temporary state file must not be a symlink')
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=True) + '\n', encoding='utf-8')
    temporary.replace(path)


def git_info(root, warnings):
    def git(*args):
        return subprocess.run(['git', '-C', str(root), *args], capture_output=True,
                              timeout=15, check=False).stdout.decode('utf-8', errors='replace').strip()
    try:
        top = git('rev-parse', '--show-toplevel')
        if not top:
            return {'commit': None, 'boundary': 'filesystem'}
        if Path(top).resolve() != root:
            warnings.append('Git belongs to an ancestor; only the explicit filesystem boundary is used.')
            return {'commit': None, 'boundary': 'filesystem'}
        return {'commit': git('rev-parse', '--verify', 'HEAD') or None,
                'boundary': 'repository'}
    except (OSError, subprocess.TimeoutExpired):
        warnings.append('Git unavailable; using filesystem fingerprints.')
        return {'commit': None, 'boundary': 'filesystem'}


def collect(root, max_files=20000, max_bytes=134217728):
    files, warnings, packages, env = [], [], [], []
    hashes, total, complete = {}, 0, True
    excluded = Counter()
    ignore_path = root / '.amanuensisignore'
    if ignore_path.is_symlink():
        raise ValueError('Ignore configuration must not be a symlink')
    patterns = []
    if ignore_path.exists():
        if ignore_path.stat().st_size > 65536:
            raise ValueError('Ignore configuration exceeds 64 KiB')
        patterns = [line.strip() for line in ignore_path.read_text(encoding='utf-8').splitlines()
                    if line.strip() and not line.lstrip().startswith('#')]

    def ignored(relative):
        for pattern in patterns:
            pattern = pattern.rstrip('/')
            if fnmatchcase(relative, pattern) or ('/' not in pattern and fnmatchcase(Path(relative).name, pattern)):
                return True
        return False

    def walk_error(error):
        nonlocal complete
        complete = False
        warnings.append(f'Cannot enumerate: {Path(error.filename).name}')

    for directory, dirs, names in os.walk(root, followlinks=False, onerror=walk_error):
        parent = Path(directory)
        kept = []
        for name in sorted(dirs):
            relative = (parent / name).relative_to(root).as_posix()
            try:
                skip = name in SKIP_DIRS or relative == 'docs/amanuensis' or ignored(relative) or linked(parent / name)
            except OSError:
                complete = False
                warnings.append(f'Cannot inspect: {relative}')
                continue
            if skip:
                excluded['directories'] += 1
            else:
                kept.append(name)
        dirs[:] = kept
        for name in sorted(names):
            path = parent / name
            relative = path.relative_to(root).as_posix()
            if ignored(relative):
                excluded['project_patterns'] += 1
                continue
            if relative == 'PROJECT_DOCUMENTATION.md':
                excluded['documentation_output'] += 1
                continue
            try:
                skip = linked(path) or name.lower() in SECRET_NAMES or path.suffix.lower() in SECRET_SUFFIXES or (name.startswith('.env') and name not in TEMPLATES)
            except OSError:
                complete = False
                warnings.append(f'Cannot inspect: {relative}')
                continue
            if skip:
                excluded['sensitive_or_linked'] += 1
                continue
            if len(files) >= max_files:
                complete = False
                warnings.append('File limit reached; increase --max-files or narrow the project.')
                dirs[:] = []
                break
            try:
                size = path.stat().st_size
                if total + size > max_bytes:
                    complete = False
                    warnings.append(f'Byte limit excludes: {relative}')
                    continue
                total += size
                # Stream hashing avoids large binaries entering model context or memory.
                hasher = hashlib.sha256()
                with path.open('rb') as stream:
                    for chunk in iter(lambda: stream.read(65536), b''):
                        hasher.update(chunk)
                hashes[relative] = hasher.hexdigest()
                files.append({'path': relative, 'bytes': size})
                if size > 1048576:
                    continue
                if name in TEMPLATES:
                    keys = sorted(set(re.findall(r'^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=', path.read_text(encoding='utf-8'), re.M)))
                    env.append({'path': relative, 'keys': keys})
                elif name == 'package.json':
                    package = json.loads(path.read_text(encoding='utf-8'))
                    packages.append({'path': relative, 'ecosystem': 'node',
                                     'dependencies': sorted(set(package.get('dependencies', {})) | set(package.get('devDependencies', {}))),
                                     'script_names': sorted(package.get('scripts', {}))})
                elif name == 'pyproject.toml':
                    package = tomllib.loads(path.read_text(encoding='utf-8'))
                    deps = package.get('project', {}).get('dependencies', [])
                    deps = [re.match(r'[A-Za-z0-9_.-]+', dep).group() for dep in deps if isinstance(dep, str) and re.match(r'[A-Za-z0-9_.-]+', dep)]
                    poetry = package.get('tool', {}).get('poetry', {})
                    deps += list(poetry.get('dependencies', {}))
                    packages.append({'path': relative, 'ecosystem': 'python',
                                     'dependencies': sorted(set(deps)),
                                     'script_names': sorted(package.get('project', {}).get('scripts', {}))})
            except (OSError, UnicodeError, ValueError, TypeError, AttributeError):
                complete = False
                warnings.append(f'Cannot inspect: {relative}')
    fingerprint = digest(json.dumps(hashes, sort_keys=True).encode())
    return {'schema_version': 1, 'scanned_at': now(), 'complete': complete,
            'fingerprint': fingerprint, 'files': files, 'hashes': hashes,
            'packages': packages, 'environment_keys': env,
            'git': git_info(root, warnings), 'warnings': warnings,
            'excluded': dict(excluded), 'bytes_hashed': total,
            'limits': {'max_files': max_files, 'max_bytes': max_bytes}}


def scan(root, args):
    manifest = collect(root, args.max_files, args.max_bytes)
    baseline = load(state_dir(root) / 'state.json', {})
    old, current = baseline.get('hashes', {}), manifest['hashes']
    changes = {'added': sorted(current.keys() - old.keys()),
               'modified': sorted(p for p in current.keys() & old.keys() if current[p] != old[p]),
               'deleted': sorted(old.keys() - current.keys())}
    manifest['changes'] = changes
    changed = set().union(*map(set, changes.values()))
    evidence = load(state_dir(root) / 'evidence-index.json', {'items': []})
    stale = []
    for item in evidence.get('items', []):
        sources = {s.split('#')[0] for s in item.get('sources', [])}
        # Runtime and uncertain dependency maps require conservative review.
        if changed and (item.get('kind') == 'runtime' or not sources or sources & changed or any(Path(p).name in LOCKFILES | {'package.json', 'pyproject.toml', 'Dockerfile'} for p in changed)):
            stale.append(item.get('id'))
    manifest['review_evidence_ids'] = stale
    save(root, 'project-manifest.json', manifest)
    summary = {k: manifest[k] for k in ('complete', 'fingerprint', 'git', 'excluded')}
    summary.update({'files': len(current), 'baseline_exists': bool(baseline),
                    'changes': {k: {'count': len(v), 'sample': v[:30]} for k, v in changes.items()},
                    'packages': manifest['packages'][:12],
                    'environment_keys': manifest['environment_keys'][:12],
                    'review_evidence_ids': stale[:40], 'warnings': manifest['warnings'][:15],
                    'manifest': '.amanuensis/project-manifest.json'})
    # Hard bound on model-facing output; full deterministic results remain on disk.
    output = json.dumps(summary, indent=2, ensure_ascii=True)
    if len(output) > 12000:
        summary.pop('packages', None)
        summary.pop('environment_keys', None)
        summary['details_omitted'] = True
        output = json.dumps(summary, indent=2, ensure_ascii=True)
    if len(output) > 12000:
        output = json.dumps({'complete': manifest['complete'], 'files': len(current),
                             'details_omitted': True, 'manifest': '.amanuensis/project-manifest.json'})
    print(output)


def validate(root):
    errors = []
    document = safe_path(root, 'PROJECT_DOCUMENTATION.md')
    if not document.is_file():
        return ['Missing PROJECT_DOCUMENTATION.md']
    text = document.read_text(encoding='utf-8')
    headings = set(re.findall(r'^## (.+?)\s*$', text, re.M))
    for section in SECTIONS:
        if section not in headings:
            errors.append('Missing section: ' + section)

    def check_link(value):
        # GitHub relative links with spaces use <...>; fragments are source locators.
        value = value.strip().strip('<>')
        parsed = urlsplit(value)
        if parsed.scheme in {'http', 'https', 'mailto'}:
            return
        if parsed.scheme or value.startswith('//'):
            errors.append('Unsupported local link: ' + value)
            return
        if not parsed.path:
            return
        try:
            path = safe_path(root, unquote(parsed.path))
            if not path.exists():
                errors.append('Missing linked file: ' + value)
        except ValueError as error:
            errors.append(str(error))

    # Ignore fenced code examples. Reference links are checked at their definitions.
    prose = re.sub(r'^(`{3,}|~{3,})[^\n]*\n.*?^\1\s*$', '', text, flags=re.M | re.S)
    for match in re.finditer(r'\]\(\s*', prose):
        start = match.end()
        if prose[start:start + 1] == '<':
            end = prose.find('>', start)
            if end != -1:
                check_link(prose[start:end + 1])
            continue
        position, depth, destination = start, 1, []
        while position < len(prose):
            char = prose[position]
            if char == '\\' and position + 1 < len(prose):
                position += 1
                destination.append(prose[position])
            elif char.isspace():
                break
            else:
                if char == '(':
                    depth += 1
                elif char == ')':
                    depth -= 1
                    if depth == 0:
                        break
                destination.append(char)
            position += 1
        if destination:
            check_link(''.join(destination))
    for match in re.finditer(r'^\s*\[[^\]]+\]:\s*(<[^>]+>|\S+)', prose, re.M):
        check_link(match.group(1))
    for match in re.finditer(r'(?:src|href)=["\']([^"\']+)["\']', prose):
        check_link(match.group(1))
    evidence = load(state_dir(root) / 'evidence-index.json', {})
    items = evidence.get('items', [])
    covered, ids = set(), set()
    for item in items:
        identifier = item.get('id')
        if not identifier or identifier in ids:
            errors.append('Evidence ids must be present and unique')
        ids.add(identifier)
        section = item.get('section')
        covered.add(section)
        if item.get('status') not in {'observed', 'inferred', 'unavailable'} or not item.get('summary'):
            errors.append(f'Invalid evidence record: {identifier}')
        if item.get('status') == 'observed':
            if not item.get('observed_at') or item.get('kind') not in {'source', 'runtime'}:
                errors.append(f'Observed evidence needs kind and observed_at: {identifier}')
            if item.get('kind') == 'source' and not item.get('sources'):
                errors.append(f'Source evidence needs sources: {identifier}')
            if item.get('kind') == 'runtime' and not item.get('procedure'):
                errors.append(f'Runtime evidence needs procedure: {identifier}')
            try:
                timestamp = datetime.fromisoformat(item.get('observed_at', '').replace('Z', '+00:00'))
                if timestamp.tzinfo is None:
                    raise ValueError('Timezone missing')
            except (ValueError, TypeError, AttributeError):
                errors.append(f'Evidence needs an ISO 8601 observation time with timezone: {identifier}')
        for value in item.get('sources', []) + item.get('assets', []):
            parsed = urlsplit(value)
            if parsed.scheme or parsed.netloc or not parsed.path:
                errors.append(f'Evidence requires a project-relative file: {value}')
                continue
            try:
                if not safe_path(root, unquote(parsed.path)).is_file():
                    errors.append(f'Missing evidence file: {value}')
            except ValueError as error:
                errors.append(str(error))
    for section in SECTIONS:
        if section not in covered:
            errors.append('Missing evidence coverage: ' + section)
    return errors


def checkpoint(root):
    manifest = load(state_dir(root) / 'project-manifest.json')
    if not manifest or not manifest['complete']:
        raise ValueError('A complete scan is required before checkpoint.')
    errors = validate(root)
    if errors:
        raise ValueError('\n'.join(errors))
    current = collect(root, **manifest['limits'])
    if not current['complete'] or current['fingerprint'] != manifest['fingerprint']:
        raise ValueError('Source changed since scan. Scan again and reconcile the changes.')
    evidence = load(state_dir(root) / 'evidence-index.json')
    for item in evidence['items']:
        if item['status'] == 'observed' and item.get('input_fingerprint') != current['fingerprint']:
            raise ValueError('Observed evidence must be reviewed against the current input_fingerprint: ' + item['id'])
    gaps = [item['id'] for item in evidence['items'] if item['status'] != 'observed']
    save(root, 'state.json', {'schema_version': 1, 'documented_at': now(),
                             'fingerprint': current['fingerprint'], 'git': current['git'],
                             'hashes': current['hashes'], 'gaps': gaps,
                             'documentation_sha256': digest((root / 'PROJECT_DOCUMENTATION.md').read_bytes()),
                             'evidence_sha256': digest((state_dir(root) / 'evidence-index.json').read_bytes())})
    print(json.dumps({'checkpoint': 'saved', 'gaps': gaps,
                      'meaning': 'Documentation baseline saved; gaps remain unverified.'}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['scan', 'validate', 'checkpoint'])
    parser.add_argument('--root', required=True, help='Explicit project directory; never defaults to a Git ancestor.')
    parser.add_argument('--max-files', type=int, default=20000)
    parser.add_argument('--max-bytes', type=int, default=134217728)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    try:
        if not root.is_dir() or root == Path(root.anchor):
            raise ValueError('Supply a project directory, not a filesystem root.')
        if args.max_files < 1 or args.max_bytes < 1:
            raise ValueError('Scan limits must be positive.')
        state_dir(root)
        if args.command == 'scan':
            scan(root, args)
        elif args.command == 'validate':
            errors = validate(root)
            if errors:
                raise ValueError('\n'.join(errors))
            print('Documentation structure, evidence records, and local link targets passed. Content accuracy requires agent review.')
        else:
            checkpoint(root)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
