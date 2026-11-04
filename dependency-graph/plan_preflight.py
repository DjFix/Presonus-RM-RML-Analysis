#!/usr/bin/env python3
"""Cheap declared physical ownership check. Never authorizes dispatch."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import time


class PlanError(ValueError):
    pass


class Files:
    def __init__(self, root):
        self.root = Path(root).resolve(strict=True)
        self.paths = {}
        self.inputs = {}

    def physical(self, name):
        if not isinstance(name, str) or not name or '\\' in name or '\x00' in name:
            raise PlanError('Expected nonempty POSIX repository-relative path')
        parts = name.split('/')
        if name.startswith('/') or any(p in ('', '.', '..') for p in parts):
            raise PlanError('Non-normalized or absolute path: ' + name)
        if name in self.paths:
            return self.paths[name]
        # Resolve links component by component; never stat/read a link target outside root.
        todo = list(parts)
        current = self.root
        links = 0
        while todo:
            part = todo.pop(0)
            if part in ('', '.'):
                continue
            if part == '..':
                if current == self.root:
                    raise PlanError('Symlink escapes repository: ' + name)
                current = current.parent
                continue
            candidate = current / part
            try:
                info = candidate.lstat()
            except FileNotFoundError:
                if current.is_dir() and any(p.name.casefold() == part.casefold() for p in current.iterdir()):
                    raise PlanError('Path casing differs from actual filesystem: ' + name)
                current = candidate
                continue
            if stat.S_ISLNK(info.st_mode):
                links += 1
                if links > 40:
                    raise PlanError('Symlink loop: ' + name)
                target = os.readlink(candidate)
                if os.path.isabs(target):
                    if target != str(self.root) and not target.startswith(str(self.root) + '/'):
                        raise PlanError('Symlink escapes repository: ' + name)
                    todo = target[len(str(self.root)):].strip('/').split('/') + todo
                    current = self.root
                else:
                    todo = target.split('/') + todo
            else:
                current = candidate
        if not current.is_relative_to(self.root):
            raise PlanError('Path escapes repository: ' + name)
        self.paths[name] = current
        return current

    def identity(self, name):
        path = self.physical(name)
        try:
            info = path.stat()
        except FileNotFoundError:
            return ('path', os.path.normcase(str(path)))
        if not stat.S_ISREG(info.st_mode):
            raise PlanError('File ownership/read path is not a regular file: ' + name)
        return ('inode', info.st_dev, info.st_ino)

    @staticmethod
    def fingerprint(info):
        return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns)

    def read_json(self, name, expected=None, retain=True):
        path = self.physical(name)
        if name in self.inputs and self.inputs[name][1] is not None:
            digest, value, before = self.inputs[name]
        else:
            before = path.stat()
            if not stat.S_ISREG(before.st_mode):
                raise PlanError('JSON input is not a regular file: ' + name)
            raw = path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            value = json.loads(raw)
            if self.fingerprint(path.stat()) != self.fingerprint(before):
                raise PlanError('Input changed while reading: ' + name)
            self.inputs[name] = (digest, value if retain else None, before)
        if expected is not None and digest != expected:
            raise PlanError('Input hash mismatch: ' + name)
        return value

    def unchanged(self):
        for name, (_, _, before) in self.inputs.items():
            # Re-resolve instead of trusting cached aliases after observation.
            self.paths.pop(name, None)
            if self.fingerprint(self.physical(name).stat()) != self.fingerprint(before):
                raise PlanError('Input changed during preflight: ' + name)


def string_list(value, label):
    if not isinstance(value, list) or any(not isinstance(p, str) or not p for p in value):
        raise PlanError(label + ' must be a list of nonempty strings')
    return value


def analyze(root, manifest_path, historical_contexts=None):
    wall, cpu = time.perf_counter(), time.process_time()
    files = Files(root)
    manifest = files.read_json(manifest_path)
    if not isinstance(manifest, dict):
        raise PlanError('Manifest must be an object')
    task_paths = string_list(manifest.get('tasks'), 'tasks')
    if not task_paths or len(set(task_paths)) != len(task_paths):
        raise PlanError('Empty or duplicate task paths')
    tasks = {}
    for path in task_paths:
        task = files.read_json(path)
        if not isinstance(task, dict) or not isinstance(task.get('task_id'), str) or not task['task_id']:
            raise PlanError('Task requires task_id: ' + path)
        ident = task['task_id']
        if ident in tasks:
            raise PlanError('Duplicate task_id: ' + ident)
        tasks[ident] = task
    groups = manifest.get('groups', [])
    if not isinstance(groups, list):
        raise PlanError('groups must be a list')
    owners = {}
    names = set()
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get('task_name'), str) or not group['task_name']:
            raise PlanError('Group requires task_name')
        name = group['task_name']
        if name in names:
            raise PlanError('Duplicate group task_name: ' + name)
        names.add(name)
        packets = string_list(group.get('packets'), 'packets')
        if not packets:
            raise PlanError('Empty group')
        for packet in packets:
            files.physical(packet)  # Validate even when output packet does not exist yet.
            ident = PurePosixPath(packet).name
            if ident not in tasks or ident in owners:
                raise PlanError('Unknown or duplicate grouped task: ' + ident)
            owners[ident] = name
    if groups and set(owners) != set(tasks):
        raise PlanError('Grouped coverage must cover tasks exactly')
    for ident in tasks:
        owners.setdefault(ident, ident)
    historical = {}
    if historical_contexts is not None:
        observations = files.read_json(historical_contexts)
        if not isinstance(observations, dict) or not isinstance(observations.get('contexts'), list):
            raise PlanError('Historical observations require contexts list')
        for ref in observations['contexts']:
            if (not isinstance(ref, dict) or set(ref) != {'task_id', 'path', 'sha256'}
                    or ref['task_id'] not in tasks or ref['task_id'] in historical
                    or not isinstance(ref['sha256'], str) or len(ref['sha256']) != 64):
                raise PlanError('Malformed or duplicate historical context reference')
            context = files.read_json(ref['path'], ref['sha256'], retain=False)
            if not isinstance(context, dict) or context.get('task_id') != ref['task_id']:
                raise PlanError('Historical context task identity mismatch')
            selected = context.get('selected_file_sha256')
            if not isinstance(selected, dict) or any(not isinstance(v, str) or len(v) != 64 for v in selected.values()):
                raise PlanError('Malformed historical selected read hashes')
            historical[ref['task_id']] = {'paths': list(selected), 'generation_sha256': context.get('generation_sha256')}
    physical_writes, physical_reads, historical_reads = {}, {}, {}
    details = {}
    canonical_destinations = {}
    for ident, task in tasks.items():
        owner = owners[ident]
        writes = string_list(task.get('owned_files'), 'owned_files')
        if not writes:
            raise PlanError('Empty owned_files: ' + ident)
        reads = string_list(task.get('declared_source_dependencies', []), 'declared_source_dependencies')
        details[ident] = {'owner': owner, 'declared_reads_present': 'declared_source_dependencies' in task,
                          'implicit_reads': 'unknown; not checked by this detector',
                          'source_proposal_map_present': 'source_proposal_map' in task,
                          'historical_context_scope': 'stale_or_unknown; never current independence' if ident in historical else 'absent',
                          'historical_generation_sha256': historical.get(ident, {}).get('generation_sha256')}
        for paths, index in [(writes, physical_writes), (reads, physical_reads),
                             (historical.get(ident, {}).get('paths', []), historical_reads)]:
            for path in paths:
                key = files.identity(path)
                index.setdefault(key, {}).setdefault(owner, set()).add(path)
        if 'source_proposal_map' in task:
            ref = task['source_proposal_map']
            if (not isinstance(ref, dict) or set(ref) != {'path', 'sha256'}
                    or not isinstance(ref['sha256'], str) or len(ref['sha256']) != 64
                    or any(c not in '0123456789abcdef' for c in ref['sha256'])):
                raise PlanError('Malformed source_proposal_map reference: ' + ident)
            mapping = files.read_json(ref['path'], ref['sha256'])
            if not isinstance(mapping, dict) or not isinstance(mapping.get('destinations'), dict) or not mapping['destinations']:
                raise PlanError('source_proposal_map requires nonempty destinations: ' + ident)
            if mapping.get('worker') != owner:
                raise PlanError('Proposal worker differs from grouped owner: ' + ident)
            seen, seen_canonical = set(), set()
            for canonical, proposal in mapping['destinations'].items():
                ck, pk = files.identity(canonical), files.identity(proposal)
                if ck in seen_canonical:
                    raise PlanError('Aliased canonical destinations in source_proposal_map: ' + ident)
                seen_canonical.add(ck)
                if pk in seen:
                    raise PlanError('Multiple canonical destinations map to one physical proposal: ' + ident)
                seen.add(pk)
                if owner not in physical_writes.get(pk, {}):
                    # A map may cover another packet within the same owner scope.
                    owned_group = {files.identity(p) for tid, t in tasks.items() if owners[tid] == owner
                                   for p in string_list(t.get('owned_files'), 'owned_files')}
                    if pk not in owned_group:
                        raise PlanError('Proposal path outside actual owned_files: ' + proposal)
                canonical_destinations.setdefault(ck, {}).setdefault(owner, set()).add(canonical)
    conflicts = []
    for key, writers in physical_writes.items():
        for owner, paths in writers.items():
            for other, other_paths in writers.items():
                if owner < other:
                    conflicts.append({'kind': 'write/write', 'owners': [owner, other],
                                      'writer_paths': sorted(paths), 'other_paths': sorted(other_paths)})
            for other, other_paths in physical_reads.get(key, {}).items():
                if owner != other:
                    conflicts.append({'kind': 'declared write/read', 'owners': [owner, other],
                                      'writer_paths': sorted(paths), 'other_paths': sorted(other_paths)})
    historical_conflicts = []
    for key, writers in physical_writes.items():
        for owner, paths in writers.items():
            for other, other_paths in historical_reads.get(key, {}).items():
                if owner != other:
                    historical_conflicts.append({'kind': 'historical write/read hint', 'owners': [owner, other],
                                                 'writer_paths': sorted(paths), 'other_paths': sorted(other_paths)})
    integration = [{'owners': sorted(own), 'canonical_paths': sorted(set().union(*own.values()))}
                   for own in canonical_destinations.values() if len(own) > 1]
    files.unchanged()
    return {'version': 1, 'outcome': 'known_conflicts_found' if conflicts or historical_conflicts else 'no_known_declared_conflicts',
            'dispatch_authorized': False, 'independence_proven': False, 'tasks': len(tasks),
            'owners': len(set(owners.values())), 'conflicts': conflicts,
            'historical_conflicts': historical_conflicts,
            'historical_context_scope': 'frozen_regression_only; stale_or_unknown_for_current_plan',
            'canonical_integration_overlaps': integration, 'task_scope': details,
            'limitations': ['Only physical writes and explicitly declared source reads are checked.',
                            'Absent declarations/mappings never prove independence.',
                            'Historical reads are conservative hints, not current generation/source/mapping verification.',
                            'Proposal destinations are not treated as worker writes; Root integration needs separate review.',
                            'No graph/claims/AST/native/provider/lifecycle/declaration/readiness verification.',
                            'Final fresh batch prepare/dispatch conflict and content checks remain mandatory.'],
            'inputs': {name: digest for name, (digest, _, _) in files.inputs.items()},
            'timing': {'wall_seconds': time.perf_counter() - wall, 'cpu_seconds': time.process_time() - cpu}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--tasks', required=True, help='Repository-relative batch manifest')
    parser.add_argument('--historical-contexts', help='Hash-bound saved contexts for frozen regression only; never current reads')
    parser.add_argument('--out', required=True, help='New repository-relative JSON receipt')
    args = parser.parse_args()
    wall, cpu = time.perf_counter(), time.process_time()
    try:
        result = analyze(args.root, args.tasks, args.historical_contexts)
        code = 1 if result['conflicts'] or result['historical_conflicts'] else 0
    except (PlanError, OSError, ValueError, TypeError) as error:
        result = {'version': 1, 'outcome': 'invalid_plan', 'dispatch_authorized': False,
                  'independence_proven': False, 'error': str(error),
                  'timing': {'wall_seconds': time.perf_counter() - wall, 'cpu_seconds': time.process_time() - cpu}}
        code = 2
    result['producer'] = {'path': 'dependency-graph/plan_preflight.py',
                          'sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    result['argv'] = [sys.executable, *sys.argv]
    result['resolved_root'] = str(Path(args.root).resolve())
    output = Files(args.root).physical(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'outcome': result['outcome'], 'dispatch_authorized': False,
                      'conflicts': len(result.get('conflicts', [])),
                      'historical_conflicts': len(result.get('historical_conflicts', [])), 'receipt': args.out,
                      'timing': result['timing']}))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
