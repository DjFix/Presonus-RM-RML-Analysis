"""Shared filesystem/task guards for subagent context packets."""
import hashlib
import json
import os
import pathlib
import re


class ContextError(ValueError):
    pass


def sha(path):
    with pathlib.Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def fingerprint(path):
    s = pathlib.Path(path).stat()
    return [s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns]


def inside(root, relative):
    p = pathlib.Path(relative)
    if p.is_absolute():
        raise ContextError('Repository-relative path required: ' + str(p))
    result = (root / p).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ContextError('Path escapes repository: ' + str(p))
    return result


def inventory(root):
    suffixes = {'.cpp', '.hpp', '.h', '.c', '.cc', '.cxx', '.inc', '.cmake'}
    paths = []
    for directory in ('uc-library/src', 'uc-library/include', 'uc-library/tests',
                      'uc-library/cmake', 'third_party/ccl-framework/core'):
        base = root / directory
        paths.extend(str(p.relative_to(root)) for p in base.rglob('*')
                     if p.is_file() and (p.suffix in suffixes or p.name == 'CMakeLists.txt'))
    return sorted(set(paths))


def validate_task(task):
    for name in ('task_id', 'objective', 'namespace'):
        if not isinstance(task.get(name), str) or not task[name].strip():
            raise ContextError('Nonempty task field required: ' + name)
    if not re.fullmatch('[a-z][a-z0-9_]{0,63}',task['task_id']):
        raise ContextError('task_id must be a valid subagent task name')
    if task.get('linkage_scope') not in (None, 'global_elf'):
        raise ContextError('Unknown linkage_scope')
    if task.get('linkage_scope') == 'global_elf' and task['namespace'] != '::':
        raise ContextError('global_elf requires exact global namespace ::')
    if not task['namespace'].rstrip(':') and task.get('linkage_scope') != 'global_elf':
        raise ContextError('Global ELF scope requires explicit linkage_scope')
    if task.get('mode') not in ('audit', 'reconstruct', 'research'):
        raise ContextError('mode must be audit, reconstruct or research')
    if not task.get('targets') or not isinstance(task['targets'], list):
        raise ContextError('Original targets are required')
    for item in task['targets']:
        elf = item.get('original_elf_sha256', '')
        if len(elf) != 64 or any(c not in '0123456789abcdef' for c in elf):
            raise ContextError('Exact original ELF SHA-256 required')
        if not item.get('mangled'):
            raise ContextError('Exact original mangled name required')
    scopes = task.get('additional_original_scopes', [])
    if not isinstance(scopes, list):
        raise ContextError('Additional scopes must be explicit original identities')
    targets = {(x['original_elf_sha256'], x['mangled'], x.get('address'), x.get('size'))
               for x in task['targets']}
    seen = set()
    for scope in scopes:
        if not isinstance(scope, dict):
            raise ContextError('Additional scope must be an identity record')
        key = (scope.get('original_elf_sha256'), scope.get('mangled'),
               scope.get('address'), scope.get('size'))
        if (key not in targets or key in seen or not isinstance(key[2], int)
                or not isinstance(key[3], int) or key[3] <= 0):
            raise ContextError('Additional scope needs an exact unique target/range')
        seen.add(key)
        namespace = scope.get('namespace', '')
        linkage = scope.get('linkage_scope')
        if linkage == 'global_cpp':
            valid = namespace == '::'
        else:
            valid = linkage is None and isinstance(namespace, str) and bool(
                re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*(?:::[A-Za-z_][A-Za-z_0-9]*)*', namespace))
        if not valid or not isinstance(scope.get('reason'), str) or not scope['reason'].strip():
            raise ContextError('Explicit C++ scope and reason required for each additional original')
    if task['mode'] == 'reconstruct' and not task.get('owned_files'):
        raise ContextError('Reconstruction requires explicit disjoint owned_files')
    if task['mode']=='audit' and task.get('owned_files'):
        raise ContextError('Audit is read-only; owned_files must be empty')
    for path in task.get('owned_files',[]):
        if pathlib.PurePosixPath(path).is_absolute() or '..' in pathlib.PurePosixPath(path).parts:
            raise ContextError('Ownership must use canonical repository paths: '+path)
        if not path.startswith(('uc-library/src/','uc-library/include/','uc-library/tests/','uc-library/candidates/')):
            raise ContextError('Shared build/ledger/vendor files stay with Root: '+path)
    if task.get('unmapped_policy', 'block') not in ('block', 'research'):
        raise ContextError('unmapped_policy must be block or research')
    if task.get('unmapped_policy') == 'research' and task['mode'] != 'research':
        raise ContextError('Unknown source mappings require an explicit research task')


def validate_original_scope(task, original):
    for scope in task.get('additional_original_scopes', []):
        if (scope['original_elf_sha256'], scope['mangled']) != (original['elf'], original['mangled']):
            continue
        if (scope['address'], scope['size']) != (original['address'], original['size']):
            raise ContextError('Additional original scope range differs')
        if scope.get('linkage_scope') == 'global_cpp':
            head = original['demangled'].split('(', 1)[0]
            if (not original['mangled'].startswith('_Z') or '::' in head
                    or '(' not in original['demangled']):
                raise ContextError('Target outside exact global C++ function scope')
        elif not re.search(r'(?<![A-Za-z0-9_])'+re.escape(scope['namespace'])+r'::', original['demangled']):
            raise ContextError('Target outside explicit additional C++ scope')
        return
    if task.get('linkage_scope') == 'global_elf':
        # Exact ELF identity/range was already resolved by enrich. This marker
        # establishes global symbol scope only, never a C prototype or ABI.
        if task['namespace'] != '::' or original['mangled'].startswith('_Z') or '::' in original['demangled']:
            raise ContextError('Target outside explicit global ELF scope: ' + original['demangled'])
    elif not re.search(r'(?<![A-Za-z0-9_])'+re.escape(task['namespace'].rstrip(':'))+r'::', original['demangled']):
        raise ContextError('Target outside assigned namespace: ' + original['demangled'])


def snapshot_guard_inputs(root, active, state):
    """Internal immutable-copy stat cache, never a live-workspace freshness override.

    The coordinator verifies copy bytes before recording fingerprints and pins the
    read-only receipt in its container invocation. A canonical path must refer to
    that independent copy before its cached fingerprint can be used. Host paths
    continue through the ordinary generation guard even if they inherit this env.
    """
    relative = os.environ.get('CONTEXT_SNAPSHOT_MANIFEST')
    expected = os.environ.get('CONTEXT_SNAPSHOT_SHA256')
    if relative is None and expected is None:
        return None
    if not relative or not expected or not re.fullmatch('[0-9a-f]{64}', expected):
        raise ContextError('Incomplete pinned snapshot receipt')
    requested = root / relative
    if requested.is_symlink() or requested.resolve() != requested:
        raise ContextError('Snapshot receipt path must be canonical')
    receipt = inside(root, relative)
    if not receipt.parent.is_relative_to(root / 'temp/recovery-work'):
        raise ContextError('Snapshot receipt must be in recovery work')
    before = fingerprint(receipt)
    raw = receipt.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected or fingerprint(receipt) != before:
        raise ContextError('Pinned snapshot receipt changed')
    manifest = json.loads(raw)
    if manifest.get('version') != 1:
        raise ContextError('Unsupported snapshot receipt version')
    if manifest.get('active') != active:
        raise ContextError('Snapshot receipt generation changed')
    copy_root = receipt.parent / 'snapshot'
    if copy_root.is_symlink() or copy_root.resolve() != copy_root or not copy_root.is_dir():
        raise ContextError('Invalid immutable snapshot root')
    fingerprints = manifest.get('guard_fingerprints', {})
    for path, item in state['files'].items():
        if manifest.get('files', {}).get(path) != item['sha256']:
            raise ContextError('Snapshot does not bind generation input: ' + path)
        value = fingerprints.get(path)
        if (not isinstance(value, list) or len(value) != 5 or
                any(not isinstance(v, int) or isinstance(v, bool) for v in value)):
            raise ContextError('Invalid snapshot fingerprint: ' + path)
        candidate = copy_root / path
        if candidate.is_symlink() or not candidate.resolve().is_relative_to(copy_root):
            raise ContextError('Snapshot input escapes copied tree: ' + path)
    return copy_root, fingerprints


def guard(root, active):
    state_path = inside(root, active['state'])
    if sha(state_path) != active['state_sha256']:
        raise ContextError('Generation state hash mismatch')
    state = json.loads(state_path.read_text())
    snapshot = snapshot_guard_inputs(root, active, state)
    dirty = []
    for path, item in state['files'].items():
        file = inside(root, path)
        if snapshot and file.is_file():
            copy_root, copy_fingerprints = snapshot
            copied = copy_root / path
            if (copied.is_file() and copied.stat().st_nlink == 1 and
                    os.path.samefile(file, copied) and fingerprint(file) == copy_fingerprints[path]):
                continue
        if not file.is_file() or fingerprint(file) != item['fingerprint']:
            if not file.is_file() or sha(file) != item['sha256']:
                dirty.append(path)
    current = inventory(root)
    if current != state['source_inventory']:
        dirty.extend(sorted(set(current) ^ set(state['source_inventory'])))
    if dirty:
        raise ContextError('Graph is stale; refresh and register before dispatch: ' +
                           json.dumps(sorted(set(dirty))[:30]))
    return state
