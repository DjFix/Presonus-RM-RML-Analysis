"""Shared filesystem/task guards for subagent context packets."""
import hashlib
import json
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


def guard(root, active):
    state_path = inside(root, active['state'])
    if sha(state_path) != active['state_sha256']:
        raise ContextError('Generation state hash mismatch')
    state = json.loads(state_path.read_text())
    dirty = []
    for path, item in state['files'].items():
        file = inside(root, path)
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
