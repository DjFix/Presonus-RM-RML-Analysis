"""Validate actual Linux compiler depfiles for SQLite-only recovery deliveries."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys

from canonical_compile_bindings import archive_contains, digest, make_dependencies

KINDS = frozenset(('ctest', 'installed_role'))
LOCAL_KINDS = frozenset(('local_replay', 'local_production'))
MANAGED = ('uc-library/', 'third_party/')
SOURCE = ('uc-library/include/', 'uc-library/src/', 'third_party/')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def member(root, value):
    relative = Path(value)
    candidate = root / relative
    require(not relative.is_absolute() and '..' not in relative.parts
            and candidate.resolve().is_relative_to(root), 'Unsafe repository path: ' + value)
    return candidate


def bind(root, reference):
    path = member(root, reference['path'])
    require(path.is_file() and digest(path) == reference['sha256'], 'Stale proof file: ' + reference['path'])
    return path


def inspect(canonical, workspace, proof, scope):
    canonical, workspace = canonical.resolve(), workspace.resolve()
    require(proof['version'] == scope['version'] == 1 and canonical != workspace,
            'Versioned canonical/physical states required')
    approved_owned = scope.get('owned_artifact_hashes', {})
    approved_generated = scope.get('generated_artifact_hashes', {})
    phase = scope.get('phase', 'canonical_postbuild')
    require(phase in ('canonical_postbuild', 'worker_pretransfer'), 'Unknown dependency verification phase')
    required_kinds = KINDS if phase == 'canonical_postbuild' else LOCAL_KINDS
    expected = {(u['kind'], u['role'], u['source']) for u in scope['required_units']}
    require(len(expected) == len(scope['required_units'])
            and {kind for kind, _, _ in expected} == required_kinds, 'Both required compiler proof scopes must be present')
    aliases = []
    for row in scope.get('provider_aliases', ()):
        local_alias = Path(row['workspace_prefix'])
        root = (local_alias if local_alias.is_absolute() else workspace/local_alias).resolve()
        require(root.is_relative_to(workspace) or root.is_relative_to(canonical/'temp/core-upstream'),
                'Provider alias outside inspected workspace or established SDK')
        provider = member(canonical, row['canonical_prefix']).resolve()
        require(root.is_dir() and provider.is_relative_to(canonical/'third_party'),
                'Exact pinned provider alias required')
        aliases.append((root, provider))
    discovered = set()
    drift = {}
    units = []
    for entry in proof['units']:
        requirement = entry['kind'], entry['role'], entry['source']
        require(requirement in expected and requirement not in discovered, 'Unexpected or duplicate compiler unit')
        discovered.add(requirement)
        source = member(workspace, entry['source'])
        working = member(workspace, entry['directory'])
        obj = bind(workspace, entry['object'])
        depfile = bind(workspace, entry['depfile'])
        dep_paths = make_dependencies(depfile, working, obj)
        require(source.resolve() in dep_paths, 'Compiler depfile does not contain the required source')
        if entry['kind'] == 'installed_role':
            archive = bind(workspace, entry['archive'])
            require(archive_contains(archive, digest(obj), obj.name), 'Installed role archive lacks the exact compiled object')
        dependencies = {}
        object_timestamp = obj.stat().st_mtime_ns
        for physical in sorted(dep_paths):
            require(physical.stat().st_mtime_ns <= object_timestamp,
                    'Dependency newer than compiled object; rebuild and replay: ' + str(physical))
            relative = None
            canonical_file = None
            if physical.is_relative_to(workspace):
                relative = str(physical.relative_to(workspace))
                if relative in approved_owned or relative in approved_generated:
                    expected_hash = (approved_owned if relative in approved_owned else approved_generated)[relative]
                    require(digest(physical) == expected_hash, 'Approved artifact changed: ' + relative)
                    dependencies[relative] = {'sha256': expected_hash, 'binding': 'approved scoped artifact'}
                    continue
                if relative.startswith(MANAGED):
                    canonical_file = member(canonical, relative)
            if canonical_file is None:
                for prefix, provider in aliases:
                    if physical.is_relative_to(prefix):
                        canonical_file = provider / physical.relative_to(prefix)
                        relative = str(canonical_file.relative_to(canonical))
                        break
            if canonical_file is None and physical.is_relative_to(canonical):
                relative = str(physical.relative_to(canonical))
                if relative.startswith(MANAGED):
                    canonical_file = physical
            if canonical_file is None:
                require(any(physical.is_relative_to(Path(system)) for system in
                            ('/usr/include', '/usr/lib/gcc', '/usr/lib/clang', '/usr/lib/llvm')),
                        'Unbound compiler dependency: ' + str(physical))
                continue
            require(canonical_file.is_file(), 'No current canonical dependency: ' + relative)
            actual, wanted = digest(physical), digest(canonical_file)
            dependencies[relative] = {'sha256': actual, 'canonical_sha256': wanted}
            if actual != wanted:
                require(relative.startswith(SOURCE) and physical.is_relative_to(workspace),
                        'Non-source or external dependency drift requires reviewed reprovisioning: ' + relative)
                item = drift.setdefault(relative, {'workspace': str(physical.relative_to(workspace)),
                    'old_sha256': actual, 'canonical_sha256': wanted, 'scopes': []})
                require(item['old_sha256'] == actual and item['canonical_sha256'] == wanted,
                        'Same canonical dependency resolved to multiple worker contents')
                item['scopes'].append({'kind': entry['kind'], 'role': entry['role'], 'source': entry['source']})
        require(dependencies, 'An empty repository dependency closure cannot pass')
        units.append({'kind': entry['kind'], 'role': entry['role'], 'source': entry['source'],
                      'object': entry['object'], 'depfile': entry['depfile'], 'dependencies': dependencies})
    require(discovered == expected, 'Missing required CTest or installed-role compiler unit')
    return {'version': 1, 'phase': phase, 'passed': not drift, 'canonical': str(canonical), 'workspace': str(workspace),
            'units': units, 'drift': drift, 'requires_fresh_compile_and_replay_after_hydration': bool(drift)}


def hydrate(canonical, workspace, verdict, output):
    canonical, workspace = canonical.resolve(), workspace.resolve()
    require(verdict['version'] == 1 and not verdict['passed'] and verdict['drift']
            and verdict['canonical'] == str(canonical) and verdict['workspace'] == str(workspace),
            'A matching failed dependency verdict is required')
    require(output.resolve().is_relative_to(workspace/'temp/recovery-work'), 'Hydration archive belongs in worker scratch')
    changes = []
    for path, planned in sorted(verdict['drift'].items()):
        require(path.startswith(SOURCE), 'Only exact repository source dependencies may be hydrated')
        source = member(canonical, path)
        target = member(workspace, planned['workspace'])
        require(digest(source) == planned['canonical_sha256'] and digest(target) == planned['old_sha256'],
                'Recheck drift after source moved: ' + path)
        changes.append((path, source, target, planned))
    output.mkdir(parents=True, exist_ok=False)
    for path, source, target, planned in changes:
        backup = output/'predecessors'/path
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, backup)
        require(digest(backup) == planned['old_sha256'], 'Failed to preserve predecessor dependency')
        incoming = output/'incoming'/path
        incoming.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, incoming)
        require(digest(incoming) == planned['canonical_sha256'], 'Changed source during hydration')
        os.replace(incoming, target)
        require(digest(target) == planned['canonical_sha256'], 'Unequal dependency after hydration')
        # The replacement gets a fresh mtime. A build cannot reuse an object
        # predating this hydration as fresh evidence.
    return {'hydrated': [item[0] for item in changes], 'replay_required': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--canonical', type=Path, required=True)
    parser.add_argument('--workspace', type=Path, required=True)
    cmd = parser.add_subparsers(dest='action', required=True)
    verify = cmd.add_parser('verify')
    verify.add_argument('--proof', type=Path, required=True)
    verify.add_argument('--scope', type=Path, required=True)
    copy = cmd.add_parser('hydrate')
    copy.add_argument('--verdict', type=Path, required=True)
    copy.add_argument('--verdict-sha256', required=True)
    for action in (verify, copy):
        action.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.action == 'verify':
        result = inspect(args.canonical, args.workspace, json.loads(args.proof.read_text()),
                         json.loads(args.scope.read_text()))
        with args.out.open('x') as stream:
            json.dump(result, stream, indent=2)
            stream.write('\n')
        print(json.dumps({'passed': result['passed'], 'drift': sorted(result['drift'])}))
        return 0 if result['passed'] else 1
    require(digest(args.verdict) == args.verdict_sha256, 'Hydration verdict digest mismatch')
    result = hydrate(args.canonical, args.workspace, json.loads(args.verdict.read_text()), args.out)
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    sys.exit(main())
