"""Frozen, bounded context preparation. No worker is authorized before publication."""
import concurrent.futures
import contextlib
import copy
import fcntl
import functools
import json
import os
import pathlib
import re
import shlex
import shutil
import sqlite3
import subprocess
import threading
import time
import uuid

from context_runtime import ContextError, fingerprint, guard, inside, sha, validate_task, snapshot_path, snapshot_aliases
from context_resources import choose_limits
from memgraph_endpoint import DEFAULT_DOCKER_NETWORK, memgraph_network, memgraph_uri, validate_network


def write_new(path, value):
    with path.open('x') as stream:
        stream.write(json.dumps(value, indent=2) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


def validate_tasks(tasks, groups=None):
    seen_ids, seen_originals, seen_owned = set(), set(), {}
    owners = {}
    for group in groups or []:
        for packet in group['packets']:
            ident = pathlib.PurePosixPath(packet).name
            if ident in owners:
                raise ContextError('Duplicate grouped packet')
            owners[ident] = group['task_name']
    for task in tasks:
        validate_task(task)
        if task['task_id'] in seen_ids:
            raise ContextError('Duplicate task identity')
        seen_ids.add(task['task_id'])
        originals = {(t['original_elf_sha256'], t['mangled']) for t in task['targets']}
        if len(originals) != len(task['targets']):
            raise ContextError('Duplicate original identity inside task')
        if seen_originals & originals:
            raise ContextError('Duplicate original identity')
        seen_originals.update(originals)
        owned = set(task.get('owned_files', []))
        owner = owners.get(task['task_id'], task['task_id'])
        if any(path in seen_owned and seen_owned[path] != owner for path in owned):
            raise ContextError('Conflicting file ownership')
        seen_owned.update({path: owner for path in owned})
    if not tasks:
        raise ContextError('Empty batch')


def check_dependency_inclusion(tasks, work, groups):
    scope_by_task = {pathlib.PurePosixPath(p).name: g['task_name']
                     for g in groups or [] for p in g['packets']}
    scope_work = {}
    for task, ident in zip(tasks, work):
        owner = scope_by_task.get(task['task_id'], task['task_id'])
        scope_work.setdefault(owner, set()).add(ident)
    for task in tasks:
        owner = scope_by_task.get(task['task_id'], task['task_id'])
        if not set(task.get('included_dependency_work', [])) <= scope_work[owner]:
            raise ContextError('Included dependency is outside actual grouped unique work')


def check_conflicts(entries, requests):
    if len({e['task_id'] for e in entries}) != len(entries):
        raise ContextError('Duplicate task identity')
    if len({e['generation_sha256'] for e in entries}) != 1:
        raise ContextError('Mixed graph generations')
    works = [e['work_binding']['work_item_id'] for e in entries]
    if len(set(works)) != len(works):
        raise ContextError('Duplicate unique work')
    for i, request in enumerate(requests):
        owned = set(request.get('owned_files', []))
        for j, entry in enumerate(entries):
            if i != j and owned & (set(entry['selected_file_sha256']) | set(requests[j].get('owned_files', []))):
                raise ContextError('Batch write/read overlap')


def snapshot_network(snapshot):
    """Old sealed manifests mean the original network, never today's route."""
    return validate_network(snapshot.get('docker_network', DEFAULT_DOCKER_NETWORK))


def capture_inputs(root, operator, task_paths):
    active = json.loads((root / 'dependency-graph/ACTIVE.json').read_text())
    guard(root, active)
    # Include every maintained Python producer, policy and operational pointer.
    paths = list((root / 'dependency-graph').glob('*.py'))
    registry_tools = list((root / 'uc-library/tools/registry').glob('*.py'))
    paths += registry_tools
    paths += [root / 'uc-library/tools/recovery/select_context.py',
              root / 'uc-library/tools/merge_readiness.py', root / 'AGENTS.md',
              root / 'dependency-graph/DEDUP_ACTIVE.json', root / 'dependency-graph/NATIVE_ACTIVE.json', root / 'uc-library/validation/registry-sqlite/ACTIVE.json']
    paths += [root / p for p in ('docs/worker-handoff.md', 'dependency-graph/CONTEXT_SELECTION.md',
                                 'dependency-graph/DEDUPLICATION.md', 'dependency-graph/BATCH_CONTEXT.md')]
    paths += list((root / 'uc-library').rglob('AGENTS.md'))
    endpoint = root / 'dependency-graph/state/memgraph-endpoint.json'
    if endpoint.exists():
        paths.append(endpoint)
    paths += [inside(root, p) for p in task_paths]
    from reconstruction_contract import bound_files
    for path in task_paths:
        task = json.loads(inside(root, path).read_text())
        paths += [inside(root, p) for p in bound_files(root, task)]
    return {'active': active, 'registry_tool_inventory': sorted(str(p.relative_to(root)) for p in registry_tools), 'memgraph_uri': memgraph_uri(root), 'docker_network': memgraph_network(root), 'endpoint_present': endpoint.exists(), 'instruction_inventory': sorted(str(p.relative_to(root)) for p in (root / 'uc-library').rglob('AGENTS.md')), 'tool_inventory': sorted(str(p.relative_to(root)) for p in (root / 'dependency-graph').glob('*.py')), 'files': {str(p.relative_to(root)): sha(p) for p in paths}}


def check_inputs(root, operator, frozen):
    endpoint = root / 'dependency-graph/state/memgraph-endpoint.json'
    if endpoint.exists() != frozen['endpoint_present'] or memgraph_uri(root) != frozen['memgraph_uri']:
        raise ContextError('Batch graph endpoint changed')
    if memgraph_network(root) != snapshot_network(frozen):
        raise ContextError('Batch graph Docker network changed; existing batch cannot be rerouted')
    if json.loads((root / 'dependency-graph/ACTIVE.json').read_text()) != frozen['active']:
        raise ContextError('Batch graph generation changed')
    if frozen.get('instruction_inventory') != sorted(str(p.relative_to(root)) for p in (root / 'uc-library').rglob('AGENTS.md')):
        raise ContextError('Batch instruction inventory changed')
    if frozen.get('registry_tool_inventory') != sorted(str(p.relative_to(root)) for p in (root / 'uc-library/tools/registry').glob('*.py')):
        raise ContextError('Batch registry adapter inventory changed')
    if frozen.get('tool_inventory') != sorted(str(p.relative_to(root)) for p in (root / 'dependency-graph').glob('*.py')):
        raise ContextError('Batch tool inventory changed')
    guard(root, frozen['active'])  # Includes a fresh source inventory, including additions/deletions.
    for path, digest in frozen['files'].items():
        file = inside(root, path)
        if not file.is_file() or sha(file) != digest:
            raise ContextError('Frozen batch input changed: ' + path)


SNAPSHOT_ROOTS = ('uc-library/src', 'uc-library/include', 'uc-library/tests', 'uc-library/cmake',
                  'uc-library/validation', 'third_party/ccl-framework/core',
                  'third_party/ccl-framework/build', 'temp/core-upstream',
                  'temp/recovery-work/dependency-graph/refresh', 'temp/test-work', 'uc-library/.venv/lib',
                  'uc-library/tools/registry')


def snapshot_reuse_leaves(root, prior, destination):
    """Verify hash-bound manifest lineage, returning only direct physical leaves."""
    chain = []
    seen = set()
    batch = prior
    expected_manifest = None
    while batch is not None:
        if (batch in seen or batch == destination.parent or batch.resolve() != batch
                or not batch.is_relative_to(root / 'temp/recovery-work')):
            raise ContextError('Unsafe/cyclic reuse manifest lineage')
        seen.add(batch)
        receipt = batch / 'SNAPSHOT.json'
        images = batch / 'IMAGES.json'
        for path in (receipt, images):
            if path.resolve() != path or not path.is_file() or path.stat().st_nlink != 1:
                raise ContextError('Unsafe reuse provenance file')
        before = sha(receipt)
        if expected_manifest is not None and before != expected_manifest:
            raise ContextError('Reuse origin manifest hash changed')
        manifest = json.loads(receipt.read_text())
        if manifest.get('version') != 1 or manifest.get('images') != json.loads(images.read_text()):
            raise ContextError('Reuse image/manifest provenance changed')
        chain.append((batch, receipt, before, images, sha(images), manifest))
        origin = manifest.get('reuse')
        if origin:
            relative = pathlib.Path(origin['batch'])
            if relative.is_absolute() or '..' in relative.parts:
                raise ContextError('Unsafe reuse origin path')
            batch = root / relative
            expected_manifest = origin['manifest_sha256']
        else:
            batch = None
    resolved = {}
    compiler_cache = {}
    verified = {}
    provenance_checks = []
    for batch, receipt, before, images, image_sha, manifest in reversed(chain):
        files = dict(manifest['files'])
        files.update({'external/' + p.lstrip('/'): d for p, d in manifest.get('external', {}).items()})
        aliases = snapshot_aliases(files)
        references = manifest.get('references', {})
        if set(references) - set(files):
            raise ContextError('Reference absent from original manifest files')
        origin_leaves = resolved.get((manifest.get('reuse') or {}).get('batch'), {})
        leaves = {}
        for relative, digest in files.items():
            alias = str(snapshot_path(pathlib.Path('/__snapshot_lexical_root__'), relative))
            target = snapshot_path(batch / 'snapshot', relative, allow_leaf_symlink=relative in references)
            if relative in references:
                record = references[relative]
                leaf = pathlib.Path(record['target'])
                expected = origin_leaves.get(alias)
                if record.get('kind') == 'compiler_observation':
                    from snapshot_observations import validate_record
                    expected = (validate_record(root,relative,digest,record['provenance'],compiler_cache),digest)
                if (expected is None or expected[1] != digest or leaf != expected[0]
                        or not leaf.is_absolute() or '..' in leaf.parts
                        or not target.is_symlink() or os.readlink(target) != str(leaf)
                        or target.resolve() != leaf or fingerprint(leaf) != record['fingerprint']):
                    raise ContextError('Reuse reference does not match recorded direct origin leaf: ' + relative)
            else:
                leaf = target
            if leaf.resolve() != leaf or not leaf.is_file() or leaf.stat().st_nlink != 1:
                raise ContextError('Unsafe direct reuse leaf: ' + relative)
            stamp = fingerprint(leaf)
            cache_key = (leaf, digest)
            if cache_key not in verified:
                if sha(leaf) != digest or fingerprint(leaf) != stamp:
                    raise ContextError('Corrupt direct reuse leaf: ' + relative)
                verified[cache_key] = stamp
            elif verified[cache_key] != stamp:
                raise ContextError('Direct reuse leaf changed during validation')
            leaves[alias] = (leaf, digest)
        if sha(receipt) != before or sha(images) != image_sha:
            raise ContextError('Reuse provenance changed during validation')
        provenance_checks.extend([(receipt, before), (images, image_sha)])
        resolved[str(batch.relative_to(root))] = leaves
    for (leaf, digest), stamp in verified.items():
        if fingerprint(leaf) != stamp:
            raise ContextError('Reuse leaf changed before planning')
    current = chain[0]
    return resolved[str(prior.relative_to(root))], current[2], provenance_checks


def snapshot_payloads(root, destination, files, external, reuse_snapshot, budget):
    """Preflight every byte before writes; references target sealed direct copies only."""
    if isinstance(budget, bool) or not isinstance(budget, int) or budget < 0:
        raise ContextError('Invalid snapshot physical-copy budget')
    prior = None
    references = {}
    if reuse_snapshot:
        raw_prior = pathlib.Path(reuse_snapshot)
        if raw_prior.is_absolute() or '..' in raw_prior.parts or (root / raw_prior).resolve() != root / raw_prior:
            raise ContextError('Unsafe reuse batch path')
        prior = inside(root, reuse_snapshot)
        if prior == destination.parent or not prior.is_relative_to(root / 'temp/recovery-work'):
            raise ContextError('Reuse must name another recovery batch')
        old_leaves, before, provenance_checks = snapshot_reuse_leaves(root, prior, destination)
        provenance = {'batch': str(prior.relative_to(root)), 'manifest_sha256': before}
    entries = [(p, inside(root, p), d) for p, d in files.items()]
    entries += [('external/' + p.lstrip('/'), pathlib.Path(p), d) for p, d in external.items()]
    snapshot_aliases({p:d for p,_,d in entries})
    plan = []
    total = 0
    planned_targets = set()
    compiler_cache = {}
    for relative, source, digest in entries:
        normalized = snapshot_path(destination, relative)
        alias_key = str(snapshot_path(pathlib.Path('/__snapshot_lexical_root__'), relative))
        if sha(source) != digest:
            raise ContextError('Snapshot input changed: ' + relative)
        size = source.stat().st_size
        reference = old_leaves[alias_key][0] if prior and old_leaves.get(alias_key, (None, None))[1] == digest else None
        compiler_record = None
        if reference is None:
            from snapshot_observations import candidate
            eligible = candidate(root,relative,digest,files,compiler_cache)
            if eligible:
                reference,compiler_record = eligible
        if reference and (reference.stat().st_mode & 0o777) != (source.stat().st_mode & 0o777):
            reference = None
        if reference:
            references[relative] = {'target': str(reference), 'fingerprint': fingerprint(reference)}
            if compiler_record:references[relative].update(kind='compiler_observation',sha256=digest,provenance=compiler_record)
        else:
            if normalized not in planned_targets:
                total += size
        planned_targets.add(normalized)
        plan.append((relative, source, digest, reference, size))
    if total > budget:
        raise ContextError('Snapshot physical-copy budget exceeded before payload writes: ' + str(total))
    if prior and any(sha(path) != digest for path, digest in provenance_checks):
        raise ContextError('Reuse lineage provenance changed before writes')
    from snapshot_observations import recheck
    recheck(root,references)
    # No payload directories, copies or symlinks exist before the complete budget check.
    destination.mkdir()
    fingerprints = {}
    written_targets = set()
    for relative, source, digest, reference, size in plan:
        target = snapshot_path(destination, relative, allow_leaf_symlink=bool(reference))
        target.parent.mkdir(parents=True, exist_ok=True)
        if target in written_targets:
            if relative in files:
                fingerprints[relative] = fingerprint(target)
            continue
        written_targets.add(target)
        if reference:
            if (reference.resolve() != reference or reference.stat().st_nlink != 1
                    or fingerprint(reference) != references[relative]['fingerprint']
                    or sha(reference) != digest or (prior and sha(prior / 'SNAPSHOT.json') != before)):
                raise ContextError('Reuse input changed during capture')
            target.symlink_to(reference)
        else:
            # Bound actual writes too if a non-cooperating writer grows the source.
            with source.open('rb') as incoming, target.open('xb') as outgoing:
                remaining = size
                while remaining:
                    block = incoming.read(min(1024 * 1024, remaining))
                    if not block:
                        raise ContextError('Snapshot input shortened during copy')
                    outgoing.write(block)
                    remaining -= len(block)
                if incoming.read(1):
                    raise ContextError('Snapshot input grew during copy')
            target.chmod(source.stat().st_mode & 0o777)
        value = fingerprint(target)
        if sha(target) != digest or sha(source) != digest or fingerprint(target) != value:
            raise ContextError('Snapshot capture changed: ' + relative)
        if reference and value != references[relative]['fingerprint']:
            raise ContextError('Reference fingerprint changed during capture')
        if relative in files:
            fingerprints[relative] = value
    if prior and any(sha(path) != digest for path, digest in provenance_checks):
        raise ContextError('Reuse lineage provenance changed during capture')
    recheck(root,references)
    return fingerprints, references, provenance if prior else None, total


def freeze_snapshot(root, output, frozen, requests, reuse_snapshot=None, copy_budget_bytes=64 * 1024 * 1024):
    """Copy checked generation inputs; no hard links to mutable workspace bytes."""
    manifest_path = output / 'SNAPSHOT.json'
    destination = output / 'snapshot'
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if manifest.get('memgraph_uri') != frozen['memgraph_uri']:
            raise ContextError('Frozen graph endpoint changed')
        if snapshot_network(manifest) != snapshot_network(frozen):
            raise ContextError('Frozen graph Docker network changed')
        if manifest.get('images') != json.loads((output / 'IMAGES.json').read_text()):
            raise ContextError('Pinned batch image identities changed')
        for relative, digest in manifest['files'].items():
            if sha(destination / relative) != digest:
                raise ContextError('Immutable batch snapshot modified: ' + relative)
        for path, digest in manifest.get('external', {}).items():
            if sha(destination / 'external' / path.lstrip('/')) != digest or sha(path) != digest:
                raise ContextError('External immutable compiler input changed: ' + path)
        return manifest
    if destination.exists():
        # Preserve a partial snapshot for diagnosis, then retry into a fresh tree.
        destination.rename(output / ('snapshot-interrupted-' + str(time.time_ns())))
    state = guard(root, frozen['active'])
    files = {p: value['sha256'] for p, value in state['files'].items()}
    files.update(frozen['files'])
    for relative in state['source_inventory']:
        files.setdefault(relative, sha(inside(root, relative)))
    files['dependency-graph/ACTIVE.json'] = sha(root / 'dependency-graph/ACTIVE.json')
    files[frozen['active']['state']] = frozen['active']['state_sha256']
    native_path = root / 'dependency-graph/NATIVE_ACTIVE.json'
    if native_path.exists():
        native = json.loads(native_path.read_text())
        files[native['database']] = native['sha256']
        files[native['report']] = native['report_sha256']
        connection = sqlite3.connect(inside(root, native['database']).as_uri() + '?mode=ro', uri=True)
        try:
            for path, digest in connection.execute('SELECT path,sha256 FROM inputs'):
                files[path] = digest
            wanted = {i['original']['elf'] for request in requests for i in request['originals']}
            for elf, path in connection.execute('SELECT id,path FROM binaries'):
                if elf in wanted:
                    files[path] = elf
        finally:
            connection.close()
    for request in requests:
        for payload in request['work_binding']['unique_payload_dependencies']:
            files[payload['object_path']] = payload['content_sha256']
    for request in requests:
        for item in request['originals']:
            for key in ('validation', 'behavior_validation'):
                path = (item.get('record') or {}).get(key)
                if path:
                    relative = 'uc-library/' + path
                    files[relative] = sha(inside(root, relative))
    external = {}
    for base in ('/usr/include/openssl', '/usr/include/x86_64-linux-gnu/openssl'):
        if pathlib.Path(base).is_dir():
            external.update({str(p): sha(p) for p in pathlib.Path(base).rglob('*') if p.is_file()})
    guard_fingerprints, references, reuse, physical_copy_bytes = snapshot_payloads(
        root, destination, files, external, reuse_snapshot, copy_budget_bytes)
    roots = [p for p in SNAPSHOT_ROOTS if (destination / p).is_dir()]
    mounts = roots + [p for p in files if not any(p == b or p.startswith(b + '/') for b in roots)]
    manifest = {'version': 1, 'references': references, 'reuse': reuse, 'physical_copy_bytes': physical_copy_bytes, 'active': frozen['active'], 'guard_fingerprints': guard_fingerprints, 'memgraph_uri': frozen['memgraph_uri'], 'docker_network': snapshot_network(frozen), 'files': files, 'mounts': mounts, 'external': external,
                'images': json.loads((output / 'IMAGES.json').read_text()),
                'scope': 'Independent immutable copies of every bound generation input, source inventory, instructions and producers'}
    write_new(manifest_path, manifest)
    return manifest


def require_prefreeze_artifacts_only(output):
    """Missing FROZEN permits a fresh setup only before any prepared artifacts.

    Preserve operational handles/inspect receipts and failed-attempt logs. A
    missing freeze beside requests, snapshots or any unknown state is not safe
    continuation and must never be repaired by inventing a freeze manifest.
    """
    for entry in output.iterdir():
        if entry.is_symlink():
            raise ContextError('Missing freeze beside unsafe/partial batch state: ' + str(entry))
        if entry.is_file() and (entry.name == 'coordinator.lock' or
                re.fullmatch(r'(?:environment-handles|resume-inspect)-[0-9]+\.json', entry.name)):
            continue
        if entry.is_dir() and re.fullmatch(r'attempt-[0-9]+', entry.name):
            if all(child.is_file() and not child.is_symlink() and child.name == 'FAILED.json'
                   for child in entry.iterdir()):
                continue
        raise ContextError('Missing freeze beside unsafe/partial batch state: ' + str(entry))


def previous_container_absent(result, name):
    """Only Docker's exact missing-object diagnostic for this requested name.

    Docker versions spell Error/No differently. Do not turn arbitrary inspect
    failures, permission errors, another object, or a live state into absence.
    """
    return (result.returncode == 1 and not result.stdout.strip() and
            re.fullmatch(r'(?:error(?: response from daemon)?:\s*)?no such object:\s*'
                         + re.escape(name), result.stderr.strip(), re.IGNORECASE) is not None)


class Environment:
    """Two batch-lifetime containers; individual exec calls retain separate logs."""
    def __init__(self, root, output):
        self.root, self.output = root, output
        self.names = {'runner': 'context-batch-runner-' + uuid.uuid4().hex,
                      'analysis': 'context-batch-analysis-' + uuid.uuid4().hex}
        self.started = []
        self.handle_path = output / ('environment-handles-' + str(time.time_ns()) + '.json')
        write_new(self.handle_path, {'containers': self.names, 'coordinator_pid': os.getpid()})

    def command(self, argv, tag):
        started = time.perf_counter()
        logfile = self.output / (tag + '.log')
        command_file = self.output / (tag + '.command.sh')
        with command_file.open('x') as script:
            script.write('exec ' + shlex.join(argv) + '\n')
        # Keep sg's single -c argument below Linux MAX_ARG_STRLEN even when
        # immutable per-file mounts make the complete Docker argv much larger.
        launcher = shlex.join(['/bin/sh', str(command_file)])
        with logfile.open('x') as log:
            result = subprocess.run(['sg', 'docker', '-c', launcher], cwd=self.root,
                                    stdout=log, stderr=subprocess.STDOUT)
        write_new(self.output / (tag + '.json'), {'argv': argv, 'seconds': time.perf_counter() - started,
                                                'returncode': result.returncode, 'command_file_sha256': sha(command_file)})
        if result.returncode:
            raise ContextError('Batch environment command failed: ' + str(logfile))

    def pin_images(self):
        path = self.output / 'IMAGES.json'
        if path.exists():
            self.images = json.loads(path.read_text())
            return
        images = {}
        for kind, image in [('runner', 'dependency-graph-runner:01'), ('analysis', 'dependency-graph-analysis:01')]:
            inspection = subprocess.run(['sg', 'docker', '-c', shlex.join(['docker', 'image', 'inspect', '--format', '{{.Id}}', image])], text=True, capture_output=True)
            if inspection.returncode or not inspection.stdout.strip().startswith('sha256:'):
                raise ContextError('Cannot pin batch image: ' + image)
            images[kind] = {'tag': image, 'id': inspection.stdout.strip()}
        write_new(path, images)
        self.images = images

    def start(self):
        snapshot = json.loads((self.output / 'SNAPSHOT.json').read_text())
        images = self.images
        for kind in ('runner', 'analysis'):
            argv = ['docker', 'run', '-d', '--name', self.names[kind], '--network',
                    snapshot_network(snapshot) if kind == 'runner' else 'none', '--workdir', str(self.root),
                    '-e', 'DEPENDENCY_GRAPH_ROOT=' + str(self.root),
                    '-e', 'MEMGRAPH_URI=' + snapshot['memgraph_uri'],
                    '-e', 'CONTEXT_SNAPSHOT_MANIFEST=' + str((self.output / 'SNAPSHOT.json').relative_to(self.root)),
                    '-e', 'CONTEXT_SNAPSHOT_SHA256=' + sha(self.output / 'SNAPSHOT.json'),
                    '-e', 'TMPDIR=' + str(self.output),
                    '-e', 'SQLITE_TMPDIR=' + str(self.output), '-v', str(self.root) + ':' + str(self.root) + ':ro',
                    '-v', str(self.output) + ':' + str(self.output) + ':rw',
                    '-v', str(self.output / 'snapshot') + ':' + str(self.output / 'snapshot') + ':ro',
                    '-v', str(self.output / 'SNAPSHOT.json') + ':' + str(self.output / 'SNAPSHOT.json') + ':ro']
            from snapshot_runtime import immutable_mounts
            for source,destination in immutable_mounts(self.root,self.output,snapshot):
                argv += ['-v', str(source) + ':' + str(destination) + ':ro']
            # Canonical records/claims are always checked live; sparse proof
            # overlays must not hide the operational registry.
            registry = self.root / 'uc-library/validation/registry-sqlite'
            argv += ['-v', str(registry) + ':' + str(registry) + ':ro']
            if kind == 'analysis':
                argv += ['-v', str(self.output / 'snapshot/external/usr/include/openssl') + ':/usr/include/openssl:ro',
                         '-v', str(self.output / 'snapshot/external/usr/include/x86_64-linux-gnu/openssl') + ':/usr/include/x86_64-linux-gnu/openssl:ro']
            argv += ['--user', '1000:1000', '--entrypoint', '/bin/sh', images[kind]['id'], '-c', 'exec sleep infinity']
            self.command(argv, 'environment-' + kind + '-' + str(time.time_ns()))
            self.started.append(kind)
        self.command(['docker', 'exec', self.names['runner'], 'python3', '-c',
                      'import sys,neo4j; print(sys.version); print(neo4j.__version__)'],
                     'runner-versions-' + str(time.time_ns()))
        self.command(['docker', 'exec', self.names['analysis'], 'python3', '-c',
                      'import sys; from clang import cindex; print(sys.version); print(cindex.Config.library_path)'],
                     'analysis-versions-' + str(time.time_ns()))
        self.command(['docker', 'exec', self.names['analysis'], 'clang-18', '--version'],
                     'analysis-compiler-version-' + str(time.time_ns()))

    def builder_argv(self, kind, script, args):
        # Each builder independently holds SH: orphaned docker exec retains the
        # generation barrier if its coordinator is killed.
        wrapper = ('import fcntl,runpy,sys,pathlib; '
                   'lock=open(sys.argv[1],"r"); fcntl.flock(lock,fcntl.LOCK_SH); '
                   'sys.argv=sys.argv[2:]; '
                   'sys.path.insert(0,str(pathlib.Path(sys.argv[0]).resolve().parent)); '
                   'runpy.run_path(sys.argv[0],run_name="__main__")')
        return ['docker', 'exec', self.names[kind], 'python3', '-c', wrapper,
                str(self.root / 'dependency-graph/state/context.lock'), str(script), *args]

    def selector(self, action, packets, tag):
        directory = self.output / ('selector-' + tag)
        directory.mkdir()
        write_new(directory / 'batch-run.json', {'action': action, 'packets': packets})
        script = self.root / 'dependency-graph/context_selector.py'
        args = ['batch-run', '--out', str(directory.relative_to(self.root))]
        argv = (['docker', 'exec', self.names['runner'], 'python3', str(script), *args]
                if action == 'validate' else self.builder_argv('runner', script, args))
        self.command(argv, tag)

    def slice(self, packet, tag):
        self.command(self.builder_argv('analysis', self.root / 'dependency-graph/context_slices.py', [str(self.root / packet)]), tag)

    def check_previous(self):
        for path in self.output.glob('environment-handles-*.json'):
            if path == self.handle_path:
                continue
            handles = json.loads(path.read_text())
            for name in handles['containers'].values():
                result = subprocess.run(['sg', 'docker', '-c', shlex.join(
                    ['docker', 'inspect', '--format', '{{.State.Running}}', name])],
                    cwd=self.root, text=True, capture_output=True)
                write_new(self.output / ('resume-inspect-' + str(time.time_ns()) + '.json'),
                          {'argv': result.args, 'returncode': result.returncode,
                           'stdout': result.stdout, 'stderr': result.stderr})
                if previous_container_absent(result, name):
                    continue
                if result.returncode or result.stdout.strip() != 'false':
                    raise ContextError('Previous batch container is live or uninspectable; inspect/resume explicitly: ' + name)

    def close(self):
        for kind in self.started:
            # Keep stopped containers and all logs available for inspection.
            try:
                self.command(['docker', 'stop', '-t', '1', self.names[kind]], 'environment-stop-' + kind + '-' + str(time.time_ns()))
            except Exception:
                pass


@contextlib.contextmanager
def locked(root, mode, timings, phase):
    before = time.perf_counter()
    with (root / 'dependency-graph/state/context.lock').open('a') as stream:
        fcntl.flock(stream, mode)
        entry = {'phase': phase, 'lock_wait_seconds': time.perf_counter() - before}
        timings.append(entry)
        held = time.perf_counter()
        try:
            yield
        finally:
            entry['lock_hold_seconds'] = time.perf_counter() - held


def acquire_request(root, operator, task, packet, resume, registry_snapshot=None):
    from dedup_work import claim_task
    enriched = operator.enrich(task, registry_snapshot)
    if not resume:
        return operator.enrich(claim_task(root, enriched, packet), registry_snapshot)
    from dedup_work import active_index, plan, validate_claim
    c, pointer = active_index(root)
    try:
        binding = plan(c, enriched)
        row = c.execute('SELECT * FROM work_claims WHERE work_item_id=? AND state="active"',
                        (binding['work_item_id'],)).fetchone()
        if row is None:
            return operator.enrich(claim_task(root, enriched, packet), registry_snapshot)
        if row['owner'] != task['task_id'] or row['packet_path'] != packet:
            raise ContextError('Resume refuses foreign claim')
        binding.update(claim_id=row['id'], claim_owner=row['owner'], claim_packet=packet,
                       database=pointer['database'])
        validate_claim(c, binding, packet)
        enriched = copy.deepcopy(enriched)
        enriched['work_binding'] = binding
        existing = {str(x['original']['anchor']) for x in enriched['originals']}
        for member in binding['covered_occurrences']:
            if member['catalog_anchor'] not in existing:
                enriched['targets'].append({'original_elf_sha256': member['elf_sha256'],
                    'mangled': member['original_mangled'], 'anchor': member['catalog_anchor']})
        return operator.enrich(enriched, registry_snapshot)
    finally:
        c.close()


def check_registry_records(operator, requests, message):
    """One new read transaction per barrier, closed before returning or raising."""
    with operator.adapter.snapshot(operator.ROOT / 'uc-library') as view:
        for request in requests:
            if operator.enrich(request, view)['originals'] != request['originals']:
                raise ContextError(message)


def _build_packet(root, packet, environment, selection, slicing, before_slice, stopped):
    """Build one packet, checking current selected reads before any AST work."""
    if stopped.is_set():
        return False
    directory = root / packet
    context = directory / 'context.json'
    ident = directory.name + '-' + str(time.time_ns())
    if not context.exists():
        if any((directory / x).exists() for x in ('TASK.md', 'CONTEXT.md', 'native-context.json')):
            raise ContextError('Interrupted selection evidence retained; manual repair required: ' + packet)
        with selection:
            if stopped.is_set():
                return False
            environment.selector('prepare', [packet], 'select-' + ident)
    if stopped.is_set():
        return False
    selected = json.loads(context.read_text())
    before_slice(packet, selected)
    packet_state = selected['state']
    if packet_state == 'selected':
        slices = directory / 'source-slices.json'
        if not slices.exists():
            with slicing:
                if stopped.is_set():
                    return False
                environment.slice(packet, 'slice-' + ident)
        with selection:
            if stopped.is_set():
                return False
            environment.selector('finalize', [packet], 'finalize-' + ident)
    elif packet_state != 'dispatch_ready':
        raise ContextError('Incomplete packet state: ' + packet)
    return True



def _with_review_validation(function):
    @functools.wraps(function)
    def wrapped(operator, *args, **kwargs):
        from execution_review import batch_validation
        with batch_validation(operator.ROOT):
            return function(operator, *args, **kwargs)
    return wrapped


@_with_review_validation
def run(operator, tasks_path, out_path, jobs='auto', selection_jobs=None, slicing_jobs=None,
        resume=False, runner_factory=Environment, resource_options=None, reuse_snapshot=None,
        copy_budget_bytes=64 * 1024 * 1024):
    root = operator.ROOT
    output = inside(root, out_path)
    if not output.is_relative_to(root / 'temp/recovery-work'):
        raise ContextError('Batch output must be project recovery work')
    source = inside(root, tasks_path)
    manifest = json.loads(source.read_text())
    items = manifest['tasks']
    task_paths = [x if isinstance(x, str) else x['task'] for x in items]
    tasks = [json.loads(inside(root, p).read_text()) for p in task_paths]
    # Reject source-port planning failures before claims, refresh or containers.
    review_gate = getattr(operator, 'validate_reconstruction_plan', None)
    if review_gate:
        for task in tasks:
            review_gate(task)
    groups = manifest.get('groups')
    allow_smaller = manifest.get('allow_smaller') is True
    flexible_total = manifest.get('flexible_total')
    production_continuation = manifest.get('production_continuation')
    if production_continuation is not None and (
            not isinstance(production_continuation, str) or not production_continuation.strip()
            or not groups or not allow_smaller or flexible_total is not None):
        raise ContextError('Production continuation requires an explicit scope and bounded grouped mode')
    if flexible_total is not None and (flexible_total != 200 or not groups or allow_smaller):
        raise ContextError('Flexible trial requires200 targets, grouped scopes, and no smaller mode')
    if allow_smaller and not manifest.get('smaller_batch_authorization'):
        raise ContextError('Explicit smaller-batch authorization required in manifest')
    validate_tasks(tasks, groups)
    # All packet outputs live below the one writable batch mount.
    packets = [str((output / 'packets' / t['task_id']).relative_to(root)) for t in tasks]
    if any(isinstance(x, dict) and x.get('packet', p) != p for x, p in zip(items, packets)):
        raise ContextError('Explicit packet path must equal batch/packets/task_id')
    timings = []
    output.mkdir(parents=True, exist_ok=resume)
    owner_lock = (output / 'coordinator.lock').open('a')
    try:
        fcntl.flock(owner_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        owner_lock.close()
        raise ContextError('Batch coordinator is already running; inspect before resuming')
    attempt = output / ('attempt-' + str(time.time_ns()))
    attempt.mkdir()
    state_path = output / 'FROZEN.json'
    environment = runner_factory(root, output)
    work_validator = None
    try:
        if resume and isinstance(environment, Environment):
            environment.check_previous()
        with locked(root, fcntl.LOCK_EX, timings, 'setup'):
            memgraph_uri(root)  # Infrastructure migration must block before claims.
            before_hashes = {p: sha(inside(root, p)) for p in task_paths + [tasks_path]}
            if json.loads(source.read_text()) != manifest or any(json.loads(inside(root,p).read_text()) != t for p,t in zip(task_paths,tasks)):
                raise ContextError('Tasks changed while acquiring setup lock')
            if resume and state_path.exists():
                frozen = json.loads(state_path.read_text())
                if frozen['manifest_sha256'] != sha(source):
                    raise ContextError('Resume manifest changed')
                check_inputs(root, operator, frozen['inputs'])
            else:
                if resume:
                    require_prefreeze_artifacts_only(output)
                from dedup_work import active_index, plan
                with operator.adapter.snapshot(root / 'uc-library') as planning_view:
                    enriched = [operator.enrich(t, planning_view) for t in tasks]
                c, pointer = active_index(root)
                try:
                    work = [plan(c, t)['work_item_id'] for t in enriched]
                finally:
                    c.close()
                if len(set(work)) != len(work):
                    raise ContextError('Duplicate unique work before claiming')
                check_dependency_inclusion(tasks, work, groups)
                before = time.perf_counter()
                operator.ensure_fresh()
                timings.append({'phase': 'refresh', 'seconds': time.perf_counter() - before})
                frozen = {'version': 1, 'manifest_sha256': sha(source), 'packets': packets,
                          'inputs': capture_inputs(root, operator, task_paths + [tasks_path])}
                if before_hashes != {p: sha(inside(root, p)) for p in before_hashes}:
                    raise ContextError('Task inputs changed during setup')
                write_new(state_path, frozen)
            requests = []
            with operator.adapter.snapshot(root / 'uc-library') as setup_view:
                for task, packet in zip(tasks, packets):
                    before = time.perf_counter()
                    directory = root / packet
                    request_path = directory / 'request.json'
                    if request_path.exists():
                        request = json.loads(request_path.read_text())
                        expected = acquire_request(root, operator, task, packet, True, setup_view)
                        for value in (request, expected):
                            value.pop('registry_guard', None)
                        if request != expected:
                            raise ContextError('Resume request differs from frozen task/claim/records')
                    else:
                        # Exact owner/path matching permits recovery of the claim/write
                        # crash window. Never release or acquire another owner's work.
                        request = acquire_request(root, operator, task, packet, resume, setup_view)
                        directory.mkdir(parents=True, exist_ok=True)
                        write_new(request_path, request)
                    member = directory / 'BATCH_MEMBER.json'
                    if not member.exists():
                        write_new(member, {'version': 1, 'manifest': str((output / 'BATCH_DISPATCH.json').relative_to(root)), 'state': 'pending'})
                    requests.append(request)
                    timings.append({'phase': 'claim/enrich', 'packet': packet, 'seconds': time.perf_counter() - before})
            check_dependency_inclusion(tasks, [q['work_binding']['work_item_id'] for q in requests], groups)
            from context_work_batch import BatchWorkValidator
            setup_validator = BatchWorkValidator(root)
            try:
                for request, packet in zip(requests, packets):
                    setup_validator.validate(request, packet)
                setup_validator.finish()
            finally:
                setup_validator.close()
            before = time.perf_counter()
            if isinstance(environment, Environment):
                environment.pin_images()
                freeze_snapshot(root, output, frozen['inputs'], requests, reuse_snapshot, copy_budget_bytes)
            timings.append({'phase': 'immutable_snapshot', 'seconds': time.perf_counter() - before})
        limits = choose_limits(jobs, len(tasks), selection_jobs=selection_jobs, slicing_jobs=slicing_jobs, **(resource_options or {}))
        write_new(attempt / 'resources.json', limits)
        write_new(attempt / 'process.json', {'pid': os.getpid(), 'started_epoch': time.time(), 'packets': packets})
        selection = threading.Semaphore(limits['limits']['selection'])
        slicing = threading.Semaphore(limits['limits']['slicing'])
        environment.start()
        with locked(root, fcntl.LOCK_SH, timings, 'builders'):
            check_inputs(root, operator, frozen['inputs'])
            from early_conflicts import EarlyConflict, SelectedReadGuard
            by_packet = dict(zip(packets, requests))
            read_guard = SelectedReadGuard(by_packet,
                frozen['inputs']['active']['state_sha256'],
                {p: sha(root/p/'request.json') for p in packets}, groups or None)
            stopped = threading.Event()
            failure_lock = threading.Lock()
            def before_slice(packet, selected):
                before = time.perf_counter()
                try:
                    read_guard.check(packet, selected, by_packet[packet])
                except EarlyConflict as error:
                    with failure_lock:
                        if not stopped.is_set():
                            stopped.set()
                            write_new(attempt/'EARLY_CONFLICT.json', error.detail)
                    raise ContextError('Early selected-read conflict; claims retained: ' + str(error)) from error
                finally:
                    timings.append({'phase': 'pre-slice-conflict-check',
                        'packet': packet, 'seconds': time.perf_counter()-before})
            def build(packet):
                return _build_packet(root, packet, environment, selection, slicing,
                                     before_slice, stopped)
            with concurrent.futures.ThreadPoolExecutor(max_workers=limits['limits']['builders']) as pool:
                futures = [pool.submit(build, p) for p in packets]
                errors = []
                for future in futures:
                    try:
                        future.result()
                    except Exception as exc:
                        errors.append(str(exc))
                if errors:
                    raise ContextError('Batch builders failed; no launch authorization: ' + json.dumps(errors))
        with locked(root, fcntl.LOCK_EX, timings, 'publication'):
            common_start = time.perf_counter()
            check_inputs(root, operator, frozen['inputs'])
            seals = {p: sha(root / p / 'context.json') for p in packets}
            entries = [json.loads((root / p / 'context.json').read_text()) for p in packets]
            check_registry_records(operator, requests, 'Selected registry records changed during preparation')
            from context_work_batch import BatchWorkValidator
            work_validator = BatchWorkValidator(root)
            for entry, packet in zip(entries, packets):
                work_validator.validate(entry, packet)
            if groups:
                from group_dispatch import check_groups
                count = len(groups[0]['packets'])
                check_groups(groups, dict(zip(packets, entries)), dict(zip(packets, requests)), count, allow_smaller, flexible_total,
                             production_continuation)
            else:
                check_conflicts(entries, requests)
            timings.append({'phase': 'common_checks', 'seconds': time.perf_counter() - common_start})
            environment.selector('validate', packets, 'validation-' + str(time.time_ns()))
            # External writers are outside flock: recheck after long validation too.
            check_inputs(root, operator, frozen['inputs'])
            check_registry_records(operator, requests, 'Selected registry records changed before publication')
            work_validator.finish()
            workers = [{'packet': p, 'context_sha256': sha(root / p / 'context.json'),
                        'arguments': {'task_name': r['task_id'], 'fork_turns': 'none',
                                      'message': (root / p / 'SUBAGENT_PROMPT.md').read_text() +
                                      ' Context manifest SHA-256: ' + sha(root / p / 'context.json')}}
                       for p, r in zip(packets, requests)]
            if groups:
                by_packet = {w['packet']: w for w in workers}
                workers = [{'packets': g['packets'], 'arguments': {
                    'task_name': g['task_name'], 'fork_turns': 'none',
                    'message': 'You own all sealed packets in this group. Read every packet before editing. '
                        + 'Scope rationale: ' + g['scope_reason']
                        + '\nExecution order: ' + json.dumps(g['execution_order'])
                        + '\nDeliver one HANDOFF v1 per exact packet identity; seal shared file hashes after all methods finish. '
                        + 'Do not spawn agents. Root owns global build and readiness integration.\n\n'
                        + '\n\n'.join(by_packet[p]['arguments']['message'] for p in g['execution_order'])}}
                    for g in groups]
            from context_publication import publish_batch, verify_packet_files
            verify_packet_files(root, packets, seals)
            if isinstance(environment, Environment):
                snapshot = json.loads((output / 'SNAPSHOT.json').read_text())
                if snapshot.get('images') != environment.images or snapshot.get('images') != json.loads((output / 'IMAGES.json').read_text()):
                    raise ContextError('Pinned image evidence changed before publication')
                for path, digest in snapshot.get('external', {}).items():
                    if sha(path) != digest:
                        raise ContextError('External compiler input changed before publication: ' + path)
            from execution_review import check_batch_validation
            check_batch_validation()
            publish_start = time.perf_counter()
            payload = {'version': 1, 'generation': frozen['inputs']['active']['state_sha256'],
                       'workers': workers, 'mode': 'sealed_before_first_worker_write',
                       'dependency_conflicts': []}
            if flexible_total is not None:
                payload['flexible_total'] = flexible_total
                payload['maximum_packets_per_worker'] = 25
            if allow_smaller:
                payload['smaller_batch_authorization'] = manifest['smaller_batch_authorization']
            if production_continuation:
                payload['production_continuation'] = production_continuation
            result = output / 'BATCH_DISPATCH.json'
            if result.exists():
                if not resume:
                    raise ContextError('Batch already published; explicit resume required')
                from context_publication import authorization
                for packet in packets:
                    authorization(root, root / packet)
                previous = json.loads(result.read_text())
                if any(previous.get(key) != value for key, value in payload.items()):
                    raise ContextError('Published batch differs from resumed payload')
            else:
                result = publish_batch(root, output, payload, packets)
            timings.append({'phase': 'atomic_publication', 'seconds': time.perf_counter() - publish_start})
            write_new(attempt / 'COMPLETED.json', {'manifest': str(result), 'timings': timings})
            return result
    except BaseException as exc:
        write_new(attempt / 'FAILED.json', {'error': str(exc), 'timings': timings, 'claims_retained': True})
        raise
    finally:
        if work_validator is not None:
            work_validator.close()
        environment.close()
        owner_lock.close()
