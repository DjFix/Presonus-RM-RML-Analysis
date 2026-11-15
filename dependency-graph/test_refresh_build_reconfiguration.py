"""Coordinator routing for explicit build-only proof; no compiler or server runs.

The proof helper's actual file/hash semantics have separate integration tests.
Here the coordinator uses real local SQLite, row selection and stale-unit logic;
only freshness detection, configure/network entrypoints and proof result are supplied.
"""
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import refresh_graph
from code_identity import VERSION, owner_id
from context_runtime import ContextError, inventory, sha
from refresh_facts import connect
from verified_build_reconfiguration import ReconfigurationRejected


class RefreshBuildReconfigurationTests(unittest.TestCase):
    def setUp(self):
        project = Path(__file__).resolve().parents[1]
        scratch = project / 'temp/test-work'
        scratch.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix='refresh-build-only-', dir=scratch)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        environment = patch.dict(os.environ, TMPDIR=str(self.root), SQLITE_TMPDIR=str(self.root))
        environment.start()
        self.addCleanup(environment.stop)
        self.base = self.root / 'dependency-graph'
        (self.base / 'state').mkdir(parents=True)
        for name in refresh_graph.PRODUCERS:
            shutil.copyfile(project / 'dependency-graph' / name, self.base / name)
        self.build = self.root / 'build'
        self.groups = [('app', self.build), ('core', self.build / 'upstream-core/build')]
        rows = []
        for group, directory in self.groups:
            directory.mkdir(parents=True)
            source = self.root / ('uc-library/src/' + group + '.cpp')
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text('int ' + group + '() { return 1; }\n')
            row = {'directory': str(directory), 'file': str(source),
                   'arguments': ['c++', '-c', str(source), '-o', group + '.o']}
            (directory / 'compile_commands.json').write_text(json.dumps([row]))
            (directory / 'CMakeCache.txt').write_text('CMAKE_HOME_DIRECTORY:INTERNAL=' + str(self.root / 'uc-library') + '\n')
            rows.append((owner_id(self.root, group, row), row))
        cmake = self.root / 'uc-library/cmake/tests/Relocated.cmake'
        cmake.parent.mkdir(parents=True)
        cmake.write_text('# old registration\n')
        state = {'files': {str(cmake.relative_to(self.root)): {'sha256': sha(cmake)}},
                 'source_inventory': inventory(self.root)}
        state_path = self.base / 'state/generation.json'
        state_path.write_text(json.dumps(state))
        active = {'state': str(state_path.relative_to(self.root)), 'state_sha256': sha(state_path)}
        (self.base / 'ACTIVE.json').write_text(json.dumps(active))
        cmake.write_text('# moved test registration; compiler inputs unchanged\n')
        with connect(self.base / 'state/refresh-index.sqlite') as c:
            c.execute('INSERT INTO meta VALUES(?,?)', ('identity_version', str(VERSION)))
            for owner, row in rows:
                payload = {'command': row, 'inputs': {row['file']: sha(Path(row['file']))}}
                c.execute('INSERT INTO unit_observations VALUES(?,?,?)',
                          (owner, owner + '-observation', json.dumps(payload)))
        self.original_plan = self.root / 'original-plan.json'
        self.original_plan.write_text(json.dumps({'producer_sha256': {'captured': 'original'}}))
        self.events = []
        for name, value in [('ROOT', self.root), ('BASE', self.base),
                            ('BUILD', self.build), ('GROUPS', self.groups)]:
            replacement = patch.object(refresh_graph, name, value)
            replacement.start()
            self.addCleanup(replacement.stop)
        for name, kwargs in [
                ('guard', {'side_effect': ContextError('fixture current CMake differs')}),
                ('run', {'side_effect': self.configure_or_inventory}),
                ('docker', {'side_effect': self.transport}),
                ('compiler_invalidation', {'return_value': (True, 'test CMake normally invalidates all')})]:
            replacement = patch.object(refresh_graph, name, **kwargs)
            mock = replacement.start()
            self.addCleanup(replacement.stop)
            setattr(self, name + '_mock', mock)
        replacement = patch('verified_build_reconfiguration.verify_build_only', side_effect=self.valid_proof)
        self.proof = replacement.start()
        self.addCleanup(replacement.stop)

    def configure_or_inventory(self, argv, out, label):
        self.events.append(label)
        (out / (label + '.json')).write_text(json.dumps({'argv': argv, 'returncode': 0}))
        if label == 'ctest-inventory':
            (out / 'ctest-inventory.log').write_text(json.dumps({'tests': []}))
        else:
            self.assertIn(label, ('configure-app', 'configure-core'))

    def valid_proof(self, root, c, rows, changed, inventory_delta, builds, producers):
        self.events.append('proof')
        self.assertEqual(root, self.root)
        self.assertEqual(len(rows), 2)
        self.assertEqual(builds, self.groups)
        self.assertEqual(producers, {'captured': 'original'})
        self.assertEqual(c.execute('SELECT count(*) FROM units').fetchone()[0], 2)
        return {'passed': True, 'units_verified': 2, 'publication_required': True,
                'graph_freshness_claimed': False}

    def transport(self, script, out, label, analysis=False):
        self.events.append(label)
        self.assertEqual(label, 'publish', 'Compiler extraction must never run on this route')
        self.assertFalse(analysis)
        self.assertEqual(script, refresh_graph.publisher_script(out))

    def test_verified_exact_proof_skips_extraction_but_still_publishes_build_facts(self):
        result = refresh_graph.ensure_fresh(verify_build_plan=self.original_plan)
        self.assertTrue(result['refreshed'])
        self.assertEqual(result['recompiled_units'], 0)
        self.assertEqual(result['reprocessed_fact_units'], 0)
        self.assertEqual(result['reused_units'], 2)
        self.assertEqual(self.events, ['configure-app', 'configure-core', 'ctest-inventory', 'proof', 'publish'])
        self.proof.assert_called_once()
        self.assertEqual(self.docker_mock.call_count, 1)
        out = self.root / result['out']
        plan = json.loads((out / 'plan.json').read_text())
        self.assertFalse(plan['compiler_invalidation_all'])
        self.assertEqual(plan['affected_units'], [])
        self.assertEqual(json.loads((out / 'units.json').read_text()), [])
        binding = plan['build_reconfiguration_proof']
        self.assertEqual(sha(Path(binding['path'])), binding['sha256'])
        proof = json.loads(Path(binding['path']).read_text())
        self.assertEqual(proof['original_plan_sha256'], sha(self.original_plan))
        self.assertEqual(set(proof['configure_receipts']), {'app', 'core'})

    def test_rejected_proof_stops_before_extractor_and_publisher(self):
        self.proof.side_effect = ReconfigurationRejected('changed input fixture')
        with self.assertRaisesRegex(ReconfigurationRejected, 'changed input'):
            refresh_graph.ensure_fresh(verify_build_plan=self.original_plan)
        self.proof.assert_called_once()
        self.docker_mock.assert_not_called()
        self.assertNotIn('publish', self.events)
        self.assertNotIn('extract', self.events)

    def test_full_rebuild_and_build_only_proof_are_incompatible(self):
        with self.assertRaisesRegex(ContextError, 'cannot be combined with full rebuild'):
            refresh_graph.ensure_fresh(full_rebuild=True, rebuild_authorization='isolated test',
                                       verify_build_plan=self.original_plan)
        self.proof.assert_not_called()
        self.docker_mock.assert_not_called()


if __name__ == '__main__':
    unittest.main()
