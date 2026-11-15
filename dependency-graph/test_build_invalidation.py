"""Fail-closed exception for compiler reuse across isolated test reconfiguration.

CMake still runs, command equality and captured dependency changes still go
through stale_units, and publication always rebuilds current build/CTest facts.
This does not certify arbitrary CMake as harmless: only the dedicated test tree
is eligible, with no production input or optional-include dependency on it.
"""
import json
import pathlib
import re

TESTS = pathlib.Path('uc-library/tests')
TEST_CMAKE = pathlib.Path('uc-library/cmake/tests')
SOURCES = {'.cpp', '.c', '.cc', '.cxx'}
PRODUCTION = ('uc-library/src', 'uc-library/include', 'third_party/ccl-framework/core')
OPTIONAL_INCLUDE = re.compile(rb'__has_include|__has_embed')


def compiler_invalidation(root, connection, rows, changed, inventory_delta,
                          configuration, force=False, builds=(), tests=()):
    """Return (invalidate_all, reason); rows must be read AFTER configuring.

    No cache schema changes: prior exact commands and captured project inputs
    are the evidence. Missing, unreadable or ambiguous evidence rejects reuse.
    """
    if force:
        return True, 'forced refresh'
    root = root.resolve()
    try:
        paths = {pathlib.Path(p).resolve().relative_to(root) for p in changed}
        # Only exact generated configuration outputs and current CTest executable
        # paths are derived artifacts. Never exempt a whole build directory,
        # CMakeCache, generated headers, or arbitrary executable/fixture paths.
        build_roots = {pathlib.Path(p).resolve() for p in builds}
        derived = {p / name for p in build_roots for name in
                   ('compile_commands.json', 'CMakeFiles/Makefile.cmake')}
        for test in tests:
            command = test.get('command', [])
            if command and pathlib.Path(command[0]).is_absolute():
                executable = pathlib.Path(command[0]).resolve()
                if any(executable.is_relative_to(p) for p in build_roots):
                    derived.add(executable)
        artifact_paths = {p for p in paths if root / p in derived}
        paths -= artifact_paths
        delta = {pathlib.Path(p) for p in inventory_delta}
        if any(p.is_absolute() or '..' in p.parts for p in delta):
            return True, 'unrecognized inventory path'
        # New headers can alter optional includes in any TU; no leaf exception.
        if any(p.suffix not in SOURCES and not (p.is_relative_to(TEST_CMAKE) and
                (p.suffix == '.cmake' or p.name == 'CMakeLists.txt')) for p in delta):
            return True, 'header or unknown inventory change'
        eligible = lambda p: p.is_relative_to(TESTS) or p.is_relative_to(TEST_CMAKE)
        production_leaf = lambda p: (p.suffix in SOURCES | {'.h', '.hpp', '.inc'} and
                                      any(p.is_relative_to(base) for base in PRODUCTION))
        isolated_configuration = bool(artifact_paths) or any(eligible(p) for p in paths)
        # Existing production leaves may change alongside isolated test CMake.
        # stale_units still invalidates every captured dependent owner. New or
        # removed production paths cannot use this exception.
        if (not isolated_configuration or
                not all(eligible(p) or production_leaf(p) for p in paths) or
                not all(eligible(p) for p in delta)):
            known_leaves = all(eligible(p) or production_leaf(p) for p in paths)
            return bool(configuration) or not known_leaves, 'outside isolated test boundary'
        old = {owner: json.loads(payload) for owner, payload in connection.execute('SELECT * FROM units')}
        current = dict(rows)
        production = lambda row: not pathlib.Path(row['file']).resolve().relative_to(root).is_relative_to(TESTS)
        previous_production = {o for o, p in old.items() if production(p['command'])}
        current_production = {o for o, row in rows if production(row)}
        if not previous_production or previous_production != current_production:
            return True, 'production translation-unit inventory changed'
        checked = set()
        for owner in previous_production:
            payload = old[owner]
            # Command changes are handled by stale_units, even if they originate
            # in a test script. Production using any test input is not isolated.
            inputs = payload['inputs']
            source = str(pathlib.Path(current[owner]['file']).resolve())
            if not inputs or source not in inputs:
                return True, 'missing captured production inputs'
            for name in inputs:
                path = pathlib.Path(name).resolve()
                relative = path.relative_to(root)
                if relative in artifact_paths:
                    return True, 'derived artifact is a production compiler input'
                if eligible(relative):
                    return True, 'production depends on test input'
                if path in checked:
                    continue
                checked.add(path)
                if OPTIONAL_INCLUDE.search(path.read_bytes().replace(b'\\\n', b'').replace(b'\\\r\n', b'')):
                    return True, 'optional include in production input'
        return False, 'isolated tests; compare every command and captured input'
    except (OSError, ValueError, KeyError, TypeError):
        return True, 'incomplete isolation evidence'
