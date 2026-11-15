"""Fresh all-unit build-only proof on tiny project-local files and memory SQL."""
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest

from verified_build_reconfiguration import verify_build_only, ReconfigurationRejected


class BuildOnlyVerificationTests(unittest.TestCase):
    def setUp(self):
        project = Path(__file__).resolve().parents[1]
        scratch = project / 'temp/test-work'
        scratch.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix='build-only-proof-', dir=scratch)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / 'dependency-graph').mkdir()
        self.producers = {}
        for name in ('refresh_extract', 'full_source_graph', 'gcc_source_graph',
                     'code_identity', 'context_runtime', 'context_resources'):
            path = self.root / 'dependency-graph' / (name + '.py')
            shutil.copyfile(project / 'dependency-graph' / path.name, path)
            self.producers['dependency-graph/' + path.name] = self.sha(path)
        self.header = self.root / 'uc-library/include/shared.hpp'
        self.header.parent.mkdir(parents=True)
        self.header.write_text('#pragma once\n')
        self.cmake = self.root / 'uc-library/cmake/tests/Relocated.cmake'
        self.cmake.parent.mkdir(parents=True)
        self.cmake.write_text('# test registration moved\n')
        self.builds = [self.root / 'app-build', self.root / 'core-build']
        self.rows = []
        self.payloads = {}
        self.c = sqlite3.connect(':memory:')
        self.addCleanup(self.c.close)
        self.c.execute('CREATE TABLE units(owner TEXT PRIMARY KEY,payload TEXT)')
        for index, group in enumerate(('app', 'core')):
            source = self.root / ('uc-library/src/' + group + '.cpp')
            source.parent.mkdir(exist_ok=True)
            source.write_text('int ' + group + '() { return 1; }\n')
            build = self.builds[index]
            build.mkdir()
            row = {'directory': str(build), 'file': str(source),
                   'arguments': ['c++', '-c', str(source), '-o', group + '.o']}
            owner = group + ':fixture'
            self.rows.append((owner, row))
            self.payloads[owner] = {'command': row, 'inputs': {
                str(source): self.sha(source), str(self.header): self.sha(self.header)}}
            (build / 'compile_commands.json').write_text(json.dumps([row]))
            (build / 'CMakeFiles').mkdir()
            (build / 'CMakeFiles/Makefile.cmake').write_text('# actual generated recipe\n')
        self.update_payloads()
        self.changed = {str(self.cmake), str(self.builds[0] / 'compile_commands.json')}
        self.inventory = {'uc-library/cmake/tests/Relocated.cmake'}

    @staticmethod
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def update_payloads(self):
        for owner, payload in self.payloads.items():
            self.c.execute('INSERT OR REPLACE INTO units VALUES(?,?)', (owner, json.dumps(payload)))
        self.c.commit()

    def verify(self, **kwargs):
        values = dict(root=self.root, c=self.c, current_rows=self.rows,
                      changed=self.changed, inventory_delta=self.inventory,
                      builds=self.builds, original_extraction_producers=self.producers)
        values.update(kwargs)
        return verify_build_only(**values)

    def test_all_units_verified_shared_header_hashed_once_no_database_mutation(self):
        before = tuple(self.c.iterdump())
        changes = self.c.total_changes
        result = self.verify()
        self.assertTrue(result['passed'])
        self.assertEqual(result['units_verified'], 2)
        self.assertEqual(result['captured_files_hashed'], 3)  # Two sources, ONE shared header.
        self.assertEqual(result['captured_bytes_read'],
                         sum(Path(p).stat().st_size for p in {
                             path for data in self.payloads.values() for path in data['inputs']}))
        self.assertTrue(result['publication_required'])
        self.assertFalse(result['graph_freshness_claimed'])
        self.assertFalse(result['registration_performed'])
        self.assertEqual(tuple(self.c.iterdump()), before)
        self.assertEqual(self.c.total_changes, changes)

    def test_exact_core_command_change_rejected_not_just_production_subset(self):
        owner, row = self.rows[1]
        changed = dict(row, arguments=row['arguments'] + ['-DNEW=1'])
        with self.assertRaisesRegex(ReconfigurationRejected, 'compile command changed'):
            self.verify(current_rows=[self.rows[0], (owner, changed)])

    def test_missing_core_owner_rejected(self):
        with self.assertRaisesRegex(ReconfigurationRejected, 'ALL old/current owners'):
            self.verify(current_rows=self.rows[:1])

    def test_added_owner_rejected(self):
        with self.assertRaisesRegex(ReconfigurationRejected, 'ALL old/current owners'):
            self.verify(current_rows=self.rows + [('new:owner', self.rows[0][1])])

    def test_changed_source_hash_rejected(self):
        Path(self.rows[0][1]['file']).write_text('int changed;\n')
        with self.assertRaisesRegex(ReconfigurationRejected, 'Captured input changed'):
            self.verify()

    def test_changed_extraction_producer_rejected(self):
        path = self.root / 'dependency-graph/full_source_graph.py'
        path.write_text(path.read_text() + '\n# changed extractor\n')
        with self.assertRaisesRegex(ReconfigurationRejected, 'Extraction producer changed'):
            self.verify()

    def test_changed_staging_producer_is_not_an_extraction_invalidator(self):
        original = dict(self.producers, **{'dependency-graph/refresh_facts.py': 'historical staging'})
        self.assertTrue(self.verify(original_extraction_producers=original)['passed'])

    def test_unknown_cmake_cache_and_generated_path_rejected(self):
        for path in (self.builds[0] / 'CMakeCache.txt', self.root / 'unknown.cfg',
                     self.builds[0] / 'CMakeFiles/Other.cmake'):
            with self.subTest(path=path), self.assertRaisesRegex(ReconfigurationRejected, 'Not an allowed'):
                self.verify(changed={str(path)})

    def test_cpp_header_inventory_delta_rejected(self):
        for path in ('uc-library/include/new.hpp', 'uc-library/src/added.cpp'):
            with self.subTest(path=path), self.assertRaisesRegex(ReconfigurationRejected, 'Not an allowed'):
                self.verify(inventory_delta={path})

    def test_conflicting_expected_shared_hashes_rejected(self):
        self.payloads[self.rows[1][0]]['inputs'][str(self.header)] = '0' * 64
        self.update_payloads()
        with self.assertRaisesRegex(ReconfigurationRejected, 'Conflicting captured'):
            self.verify()

    def test_empty_or_source_missing_inputs_rejected(self):
        owner = self.rows[0][0]
        self.payloads[owner]['inputs'] = {}
        self.update_payloads()
        with self.assertRaisesRegex(ReconfigurationRejected, 'input hashes absent'):
            self.verify()
        self.payloads[owner]['inputs'] = {str(self.header): self.sha(self.header)}
        self.update_payloads()
        with self.assertRaisesRegex(ReconfigurationRejected, 'source missing'):
            self.verify()

    def test_optional_include_and_embed_rejected_even_when_hashes_match(self):
        for token in ('__has_include', '__has_embed'):
            self.header.write_text('#if ' + token + '("optional.h")\n#endif\n')
            for payload in self.payloads.values():
                payload['inputs'][str(self.header)] = self.sha(self.header)
            self.update_payloads()
            with self.subTest(token=token), self.assertRaisesRegex(ReconfigurationRejected, 'Optional include/embed'):
                self.verify()

    def test_line_spliced_optional_constructs_rejected(self):
        for token in ('__has_incl\\\nude', '__has_em\\\r\nbed'):
            self.header.write_text('#if ' + token + '("optional.h")\n#endif\n')
            for payload in self.payloads.values():
                payload['inputs'][str(self.header)] = self.sha(self.header)
            self.update_payloads()
            with self.subTest(token=token), self.assertRaisesRegex(ReconfigurationRejected, 'Optional include/embed'):
                self.verify()

    def test_spliced_construct_across_stream_block_rejected(self):
        # Put the escape at the very end of the first 128KiB read.
        prefix = b' ' * (128 * 1024 - len(b'__has_incl') - 1)
        self.header.write_bytes(prefix + b'__has_incl\\' + b'\nude("optional.h")\n')
        for payload in self.payloads.values():
            payload['inputs'][str(self.header)] = self.sha(self.header)
        self.update_payloads()
        with self.assertRaisesRegex(ReconfigurationRejected, 'Optional include/embed'):
            self.verify()

    def test_generated_commands_must_match_reconfigured_all_unit_rows(self):
        (self.builds[1] / 'compile_commands.json').write_text('[]')
        with self.assertRaisesRegex(ReconfigurationRejected, 'Generated ALL compiler rows'):
            self.verify()

    def test_exact_generated_makefile_and_main_cmake_changes_allowed(self):
        paths = [self.root / 'uc-library/CMakeLists.txt',
                 self.builds[0] / 'CMakeFiles/Makefile.cmake',
                 self.builds[1] / 'compile_commands.json']
        self.assertTrue(self.verify(changed=paths)['passed'])

    def test_input_absent_rejected(self):
        self.header.unlink()
        with self.assertRaisesRegex(ReconfigurationRejected, 'missing/unreadable'):
            self.verify()


if __name__ == '__main__':
    unittest.main()
