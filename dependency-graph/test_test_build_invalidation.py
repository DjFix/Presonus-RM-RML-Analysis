"""Regression checks for the dedicated-test CMake reuse boundary."""
import ast
import json
import pathlib
import sqlite3
import unittest
import uuid
import shlex

from context_runtime import sha

from refresh_facts import stale_units
from test_build_invalidation import compiler_invalidation

ROOT = pathlib.Path(__file__).resolve().parents[1]


class TestBuildInvalidation(unittest.TestCase):
    def setUp(self):
        self.root = ROOT / 'temp/test-work/test-build-invalidation' / uuid.uuid4().hex
        self.root.mkdir(parents=True)
        self.c = sqlite3.connect(':memory:')
        self.c.execute('CREATE TABLE units(owner TEXT PRIMARY KEY, payload TEXT)')
        self.source = self.write('uc-library/src/p.cpp', 'int production;')
        self.header = self.write('uc-library/include/p.hpp', '// header')
        self.row = {'file': str(self.source), 'directory': str(self.root),
                    'arguments': ['c++', '-c', str(self.source), '-o', 'p.o']}
        self.inputs = {str(self.source): 'sha', str(self.header): 'sha'}
        self.save()
        self.rows = [('production', self.row)]

    def tearDown(self):
        self.c.close()

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def save(self):
        self.c.execute('INSERT OR REPLACE INTO units VALUES(?,?)',
                       ('production', json.dumps({'command': self.row, 'inputs': self.inputs})))

    def plan(self, changed, delta=(), configuration=True, force=False, builds=(), tests=()):
        absolute = [str(self.root / p) for p in changed]
        all_units, reason = compiler_invalidation(self.root, self.c, self.rows,
                                                  absolute, delta, configuration, force, builds, tests)
        return stale_units(self.c, self.rows, absolute, all_units), reason

    def test_new_and_deleted_test_sources_reuse_production(self):
        name = 'uc-library/tests/new.cpp'
        path = self.write(name, 'int main() {}')
        row = dict(self.row, file=str(path))
        self.rows.append(('test', row))
        self.assertEqual(self.plan([name], [name])[0], ({'test'}, set()))
        self.c.execute('INSERT INTO units VALUES(?,?)',
                       ('test', json.dumps({'command': row, 'inputs': {str(path): 'sha'}})))
        self.rows.pop()
        self.assertEqual(self.plan([name], [name])[0], (set(), {'test'}))

    def test_mixed_test_registration_and_existing_production_leaf(self):
        other = self.write('uc-library/src/other.cpp', 'int unrelated;')
        row = dict(self.row, file=str(other))
        self.rows.append(('unrelated', row))
        self.c.execute('INSERT INTO units VALUES(?,?)', ('unrelated', json.dumps(
            {'command': row, 'inputs': {str(other): 'sha'}})))
        for leaf in ('uc-library/src/p.cpp', 'uc-library/include/p.hpp'):
            with self.subTest(leaf=leaf):
                changed = ['uc-library/cmake/tests/CMakeLists.txt', leaf]
                self.assertEqual(self.plan(changed)[0], ({'production'}, set()))
        changed = ['uc-library/cmake/tests/CMakeLists.txt', 'uc-library/src/new.cpp']
        self.assertEqual(self.plan(changed, [changed[1]])[0][0], {'production', 'unrelated'})

    def test_current_production_command_always_compared(self):
        self.rows = [('production', dict(self.row, arguments=self.row['arguments'] + ['-DCHANGED']))]
        self.assertEqual(self.plan(['uc-library/cmake/tests/CMakeLists.txt'])[0][0], {'production'})

    def test_headers_global_cmake_unknown_and_force_fall_back(self):
        for name, delta in [('uc-library/tests/new.hpp', ['uc-library/tests/new.hpp']),
                            ('uc-library/cmake/ProductionSourceGroups.cmake', []),
                            ('unknown.cmake', []), ('uc-library/cmake/tests/new.hpp', ['uc-library/cmake/tests/new.hpp']), ('dependency-graph/refresh_extract.py', [])]:
            with self.subTest(name=name):
                self.assertEqual(self.plan([name], delta)[0][0], {'production'})
        self.assertEqual(self.plan(['uc-library/tests/x.cpp'], force=True)[0][0], {'production'})

    def test_unknown_leaf_change_is_conservative(self):
        self.assertEqual(self.plan(['unknown.py'], configuration=False)[0][0], {'production'})
        self.assertEqual(self.plan(['uc-library/src/p.cpp'], configuration=False)[0][0], {'production'})

    def test_script_fixture_and_test_cmake_reuse(self):
        for name in ['uc-library/tests/check.py', 'uc-library/tests/fixture.json',
                     'uc-library/cmake/tests/CMakeLists.txt']:
            self.assertEqual(self.plan([name])[0][0], set())

    def test_production_inclusion_of_test_input_rejects_reuse(self):
        path = self.write('uc-library/tests/shared.cpp', 'int shared;')
        self.inputs[str(path)] = 'sha'
        self.save()
        self.assertEqual(self.plan(['uc-library/tests/new.cpp'])[0][0], {'production'})

    def test_optional_include_and_missing_input_reject_reuse(self):
        self.header.write_text('#if __has_include("new.cpp")\n#endif')
        self.assertEqual(self.plan(['uc-library/tests/new.cpp'])[0][0], {'production'})
        self.header.unlink()
        self.assertEqual(self.plan(['uc-library/tests/new.cpp'])[0][0], {'production'})

    def test_production_inventory_change_rejects_reuse(self):
        self.rows.append(('extra', dict(self.row, file=str(self.root / 'uc-library/src/q.cpp'))))
        self.assertEqual(self.plan(['uc-library/tests/new.cpp'])[0][0], {'production', 'extra'})

    def test_metadata_refresh_is_unconditional_after_compiler_selection(self):
        # Exercise the actual fact producer with an explicit isolated root and
        # empty TU index: changed fixtures and RUNS must replace prior metadata.
        # Load the pure fact function without importing the network publisher
        # runtime (neo4j is intentionally absent from this host test venv).
        tree = ast.parse((ROOT / 'dependency-graph/refresh_publish.py').read_text())
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'build_facts')
        scope = dict(ROOT=self.root, json=json, pathlib=pathlib, shlex=shlex, sha=sha)
        exec(compile(ast.Module(body=[function], type_ignores=[]), 'refresh_publish.py', 'exec'), scope)
        build_facts = scope['build_facts']
        out = self.root / 'out'; out.mkdir()
        fixture = self.write('uc-library/tests/fixture.json', 'first')
        command = [str(self.root / 'runner'), str(fixture)]
        inventory = out / 'ctest-inventory.log'
        inventory.write_text(json.dumps({'tests': [{'name': 'check', 'command': command}]}))
        empty = sqlite3.connect(':memory:')
        empty.execute('CREATE TABLE units(owner TEXT, payload TEXT)')
        first = build_facts(empty, out)
        fixture.write_text('second')
        command[0] = str(self.root / 'new-runner')
        inventory.write_text(json.dumps({'tests': [{'name': 'check', 'command': command}]}))
        second = build_facts(empty, out)
        empty.close()
        self.assertNotEqual(first[2][str(fixture)], second[2][str(fixture)])
        self.assertIn(('test:check', 'file:new-runner', 'RUNS', 'current CTest inventory'), second[1])
        # Inventory is now collected before compiler selection so artifact
        # classification uses the current configured CTest commands.
        source = (ROOT / 'dependency-graph/refresh_graph.py').read_text()
        self.assertLess(source.index("out, 'ctest-inventory'"), source.index('compiler_invalidation('))
        self.assertIn("\n        docker(publisher_script(out)", source)

    def test_realistic_generated_artifacts_and_current_ctest_executables(self):
        build = self.root / 'temp/core-upstream/root-integration-01'
        artifact_names = ['compile_commands.json', 'CMakeFiles/Makefile.cmake',
                          'Replay', 'tests/recovery/worker/Replay']
        changed = ['temp/core-upstream/root-integration-01/' + p for p in artifact_names]
        tests = [{'command': [str(build / p)]} for p in artifact_names[2:]]
        name = 'uc-library/tests/new.cpp'
        self.assertEqual(self.plan(changed + [name], [name], builds=[build], tests=tests)[0][0], set())
        self.assertEqual(self.plan(changed, builds=[build], tests=tests)[0][0], set())
        self.rows = [('production', dict(self.row, arguments=self.row['arguments'] + ['-DCHANGED']))]
        self.assertEqual(self.plan(changed, builds=[build], tests=tests)[0][0], {'production'})

    def test_generated_artifact_exceptions_are_exact_and_never_inputs(self):
        build = self.root / 'temp/core-upstream/root-integration-01'
        prefix = 'temp/core-upstream/root-integration-01/'
        for name in ['CMakeCache.txt', 'unknown', 'generated.hpp', 'CMakeFiles/unknown.cmake']:
            self.assertEqual(self.plan([prefix + name], builds=[build])[0][0], {'production'})
        generated = self.write(prefix + 'compile_commands.json', '{}')
        self.inputs[str(generated)] = 'sha'; self.save()
        self.assertEqual(self.plan([prefix + 'compile_commands.json'], builds=[build])[0][0], {'production'})

    def test_fixture_change_before_and_after_test_build(self):
        name = 'uc-library/tests/fixture.json'
        self.assertEqual(self.plan([name], configuration=False)[0][0], set())
        build = self.root / 'temp/core-upstream/root-integration-01'
        executable = build / 'Replay'
        tests = [{'command': [str(executable), str(self.root / name)]}]
        changed = [name, str(executable.relative_to(self.root))]
        self.assertEqual(self.plan(changed, configuration=False, builds=[build], tests=tests)[0][0], set())
        # A global input must still defeat the artifact exception.
        self.assertEqual(self.plan(changed + ['uc-library/CMakeLists.txt'], builds=[build], tests=tests)[0][0], {'production'})


if __name__ == '__main__':
    unittest.main()
