"""Fail-closed exception for compiler reuse across isolated test reconfiguration.

CMake still runs, command equality and captured dependency changes still go
through stale_units, and publication always rebuilds current build/CTest facts.
This does not certify arbitrary CMake as harmless: only the dedicated test tree
is eligible, with no production input or optional-include dependency on it.
"""
import json
import pathlib
import re
import shlex

TESTS = pathlib.Path('uc-library/tests')
TEST_CMAKE = pathlib.Path('uc-library/cmake/tests')
SOURCES = {'.cpp', '.c', '.cc', '.cxx'}
PRODUCTION = ('uc-library/src', 'uc-library/include', 'third_party/ccl-framework/core')
OPTIONAL_INCLUDE = re.compile(rb'__has_include|__has_embed')



def _test_argument_artifacts(root, build_roots, rows, tests, changed):
    """Identify only changed, exact generated paths named by current CTest argv."""
    if not build_roots:
        return set()
    recipe_inputs = set()
    archive_outputs = set()
    for build in build_roots:
        makefile = build / 'CMakeFiles/Makefile.cmake'
        if not makefile.is_file():
            return set()
        blocks = re.findall(r'^set\(CMAKE_MAKEFILE_DEPENDS[ \t]*\n(.*?)^[ \t]*\)[ \t]*$',
                            makefile.read_text(), re.S | re.M)
        if len(blocks) != 1:
            return set()
        lines = [line.strip() for line in blocks[0].splitlines() if line.strip()]
        if not lines or any(not re.fullmatch(r'"(?:[^"\\]|\\.)+"', line) for line in lines):
            return set()
        inputs = [shlex.split(line)[0] for line in lines]
        if any(re.search(r'[$;()]', name) for name in inputs):
            return set()
        recipe_inputs.update((build / name).resolve() for name in inputs)
        for recipe in build.glob('CMakeFiles/*/link.txt'):
            for line in recipe.read_text().splitlines():
                argv = shlex.split(line)
                if (argv and pathlib.Path(argv[0]).name in ('ar', 'gcc-ar', 'llvm-ar')
                        and len(argv) >= 3 and pathlib.Path(argv[2]).suffix == '.a'):
                    archive_outputs.add((build / argv[2]).resolve())

    compiled_sources = set()
    object_outputs = set()
    for _, row in rows:
        compiled_sources.add(pathlib.Path(row['file']).resolve())
        argv = row.get('arguments') or shlex.split(row['command'])
        if '-o' in argv:
            object_outputs.add((pathlib.Path(row['directory']) / argv[argv.index('-o') + 1]).resolve())

    test_output = root / 'temp/test-work'
    artifacts = set()
    for test in tests:
        for argument in test.get('command', [])[1:]:
            candidate = pathlib.Path(argument)
            if not candidate.is_absolute():
                continue
            path = candidate.resolve()
            if (path not in changed or path in recipe_inputs or path in compiled_sources
                    or path in artifacts or not path.is_file()):
                continue
            if path.is_relative_to(test_output) and path.suffix == '.json':
                artifacts.add(path)
                continue
            if not any(path.is_relative_to(build) for build in build_roots):
                continue
            with path.open('rb') as stream:
                magic = stream.read(8)
            if ((magic.startswith(b'\x7fELF') and
                 (path in object_outputs or (not path.suffix and path.stat().st_mode & 0o111)))
                    or (magic == b'!<arch>\n' and path in archive_outputs)):
                artifacts.add(path)
    return artifacts


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
        # Exact generated configuration outputs and bounded test command artifacts
        # may be considered independently of compiler inputs. Never exempt a whole build directory,
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
        derived.update(_test_argument_artifacts(root, build_roots, rows, tests, {root / p for p in paths}))
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
