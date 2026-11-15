"""Explicit proof for already-completed build-only reconfiguration.

This helper is opt-in: it never configures, changes an index, skips publication,
registers a graph, or opens a database itself. ``builds`` is an iterable of build
root Paths (or group/Path pairs). ``original_extraction_producers`` is the exact
retained extraction producer hash map, not a newly relabelled execution record.
"""
import hashlib
import json
from pathlib import Path
import re

from reuse_observations import _closure


class ReconfigurationRejected(ValueError):
    pass


def _path(root, value):
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    if '..' in path.parts or not path.resolve().is_relative_to(root):
        raise ReconfigurationRejected('Non-project/traversing path: ' + str(value))
    return path.resolve()


def _packed(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def verify_build_only(root, c, current_rows, changed, inventory_delta, builds,
                      original_extraction_producers):
    """Return a compact fresh proof; raise ReconfigurationRejected on any mismatch.

    The caller must have already run reconfiguration and supplied its ALL-unit
    rows, not a production-only subset. Every retained captured input is freshly
    hashed once per resolved path. Changed/inventory paths have a closed allowlist.
    """
    root = Path(root).resolve()
    build_roots = []
    for entry in builds:
        value = entry[1] if isinstance(entry, (tuple, list)) and len(entry) == 2 else entry
        build = _path(root, value)
        if build == root or build in build_roots:
            raise ReconfigurationRejected('Invalid/duplicate build root')
        build_roots.append(build)
    if not build_roots:
        raise ReconfigurationRejected('Explicit reconfigured build roots required')
    generated = {build / name for build in build_roots
                 for name in ('compile_commands.json', 'CMakeFiles/Makefile.cmake')}

    def allowed(path):
        relative = path.relative_to(root)
        return (relative == Path('uc-library/CMakeLists.txt') or
                (relative.is_relative_to('uc-library/cmake') and relative.suffix == '.cmake') or
                path in generated)

    changed_paths = {_path(root, value) for value in changed}
    inventory_paths = {_path(root, value) for value in inventory_delta}
    for path in changed_paths | inventory_paths:
        if not allowed(path):
            raise ReconfigurationRejected('Not an allowed build-only change: ' + str(path.relative_to(root)))
    producers = _closure(root)
    for path, digest in producers.items():
        if original_extraction_producers.get(path) != digest:
            raise ReconfigurationRejected('Extraction producer changed/unbound: ' + path)
    current = {}
    for owner, row in current_rows:
        if owner in current or not isinstance(row, dict):
            raise ReconfigurationRejected('Duplicate/invalid current owner')
        current[owner] = row
    if not current:
        raise ReconfigurationRejected('All-unit compiler rows must be nonempty')
    old, expected_inputs = {}, {}
    for owner, text in c.execute('SELECT owner,payload FROM units ORDER BY owner'):
        if owner in old:
            raise ReconfigurationRejected('Duplicate retained owner')
        payload = json.loads(text)
        row = payload.get('command')
        if not isinstance(row, dict):
            raise ReconfigurationRejected('Captured compile command absent: ' + owner)
        old[owner] = row
        inputs = payload.get('inputs')
        if not isinstance(inputs, dict) or not inputs:
            raise ReconfigurationRejected('Captured input hashes absent: ' + owner)
        source = _path(root, row['file'])
        unit_inputs = set()
        for value, digest in inputs.items():
            path = _path(root, value)
            unit_inputs.add(path)
            if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
                raise ReconfigurationRejected('Invalid captured input hash: ' + str(path))
            if path in expected_inputs and expected_inputs[path] != digest:
                raise ReconfigurationRejected('Conflicting captured input hashes: ' + str(path))
            expected_inputs[path] = digest
        if source not in unit_inputs:
            raise ReconfigurationRejected('Captured source missing from inputs: ' + owner)
    if set(old) != set(current):
        raise ReconfigurationRejected('ALL old/current owners differ (including test/Core units)')
    for owner in old:
        if old[owner] != current[owner]:
            raise ReconfigurationRejected('Exact compile command changed: ' + owner)
    # A successful configure is a caller precondition; independently bind the
    # generated command contents to the supplied current ALL-unit row collection.
    generated_rows = set()
    build_bindings = []
    for build in build_roots:
        path = build / 'compile_commands.json'
        if not path.is_file():
            raise ReconfigurationRejected('Reconfigured compile_commands absent: ' + str(path))
        raw = path.read_bytes()
        values = json.loads(raw)
        if not isinstance(values, list) or any(not isinstance(row, dict) for row in values):
            raise ReconfigurationRejected('Invalid generated compiler rows')
        generated_rows.update(_packed(row) for row in values)
        binding = {'root': str(build), 'compile_commands_sha256': hashlib.sha256(raw).hexdigest()}
        makefile = build / 'CMakeFiles/Makefile.cmake'
        if makefile.exists():
            binding['makefile_sha256'] = hashlib.sha256(makefile.read_bytes()).hexdigest()
        build_bindings.append(binding)
    if generated_rows != {_packed(row) for row in current.values()}:
        raise ReconfigurationRejected('Generated ALL compiler rows do not match supplied rows')
    aggregate = hashlib.sha256()
    byte_count = 0
    for path, expected in sorted(expected_inputs.items()):
        try:
            # Stream hashing and optional-include scanning together, once even
            # when hundreds of owners share a header. No input payloads retained.
            digest = hashlib.sha256()
            tail = b''
            splice_pending = b''
            with path.open('rb') as stream:
                while block := stream.read(128 * 1024):
                    digest.update(block)
                    byte_count += len(block)
                    raw = splice_pending + block
                    if raw.endswith(b'\\\r'):
                        raw, splice_pending = raw[:-2], raw[-2:]
                    elif raw.endswith(b'\\'):
                        raw, splice_pending = raw[:-1], raw[-1:]
                    else:
                        splice_pending = b''
                    # C/C++ translation phase 2 joins escaped physical lines
                    # before recognizing __has_include/__has_embed tokens.
                    logical = re.sub(rb'\\\r?\n', b'', raw)
                    scanned = tail + logical
                    if b'__has_include' in scanned or b'__has_embed' in scanned:
                        raise ReconfigurationRejected('Optional include/embed construct in captured input: ' + str(path))
                    tail = scanned[-32:]
            observed = digest.hexdigest()
        except OSError as exc:
            raise ReconfigurationRejected('Captured input missing/unreadable: ' + str(path)) from exc
        if observed != expected:
            raise ReconfigurationRejected('Captured input changed: ' + str(path))
        aggregate.update(_packed([str(path), observed]) + b'\n')
    command_digest = hashlib.sha256()
    for owner in sorted(current):
        command_digest.update(_packed([owner, current[owner]]) + b'\n')
    return {'version': 1, 'passed': True, 'compiler_commands_and_inputs_unchanged': True,
            'units_verified': len(current), 'captured_files_hashed': len(expected_inputs),
            'captured_bytes_read': byte_count, 'captured_inputs_sha256': aggregate.hexdigest(),
            'all_owner_commands_sha256': command_digest.hexdigest(),
            'extraction_producers': producers, 'builds': build_bindings,
            'changed_paths_verified': len(changed_paths), 'inventory_paths_verified': len(inventory_paths),
            'reconfiguration_execution_receipt_required_from_caller': True,
            'publication_required': True, 'graph_freshness_claimed': False,
            'registration_performed': False,
            'scope': 'Explicit build-only validation after configure; normal build facts/input checks and publication remain mandatory'}
