"""Offline regressions: never create a driver or touch production storage."""
import pathlib
import tempfile
import sys
import types
import unittest
from unittest.mock import patch

from production_write_stop import (PRODUCTION_ROOT, ProductionGraphUpdatesStopped,
                                   require_graph_updates, require_graph_storage_write)


FIXTURE_ROOT = PRODUCTION_ROOT / 'temp/test-work/production-write-stop'
FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)


class StopTests(unittest.TestCase):
    def setUp(self):
        # These entrypoint regressions simulate a missing canonical policy.
        # Never depend on (or read) the operator's live maintenance permission.
        self.documents = patch('production_write_stop._document',
                               side_effect=FileNotFoundError('offline stop fixture'))
        self.document_mock = self.documents.start()
        self.addCleanup(self.documents.stop)

    def test_canonical_cannot_be_reopened_by_environment_or_removed_policy(self):
        with patch.dict('os.environ', {'ALLOW_GRAPH_WRITES': '1', 'MEMGRAPH_URI': 'bolt://unused:7687'}):
            with self.assertRaises(ProductionGraphUpdatesStopped):
                require_graph_updates(PRODUCTION_ROOT)
        self.document_mock.assert_called_once_with(
            PRODUCTION_ROOT / 'dependency-graph/PRODUCTION_GRAPH_STOP.json')

    def test_copy_policy_is_stopped_and_fixture_root_allowed(self):
        with tempfile.TemporaryDirectory(dir=FIXTURE_ROOT) as directory:
            root = pathlib.Path(directory)
            require_graph_updates(root)
            (root / 'dependency-graph').mkdir()
            (root / 'dependency-graph/PRODUCTION_GRAPH_STOP.json').write_text('{}')
            with self.assertRaises(ProductionGraphUpdatesStopped):
                require_graph_updates(root)

    def test_source_index_blocked_before_sqlite(self):
        import refresh_facts
        with patch.object(refresh_facts.sqlite3, 'connect', side_effect=AssertionError('must not connect')):
            with self.assertRaises(ProductionGraphUpdatesStopped):
                refresh_facts.connect(PRODUCTION_ROOT / 'dependency-graph/state/source.sqlite')

    def test_deferred_publication_blocked_before_session_or_log(self):
        import batch_publication
        with self.assertRaises(ProductionGraphUpdatesStopped):
            batch_publication.publish(None, None, PRODUCTION_ROOT / 'temp/recovery-work/dependency-graph/refresh/1/delta.sqlite', '/never/create/log')

    def test_refresh_register_native_and_lock_block_before_side_effects(self):
        offline_driver = types.ModuleType("neo4j")
        offline_driver.GraphDatabase = types.SimpleNamespace(driver=lambda *a, **k: self.fail("network driver forbidden"))
        with patch.dict(sys.modules, {"neo4j": offline_driver}):
            import refresh_graph, refresh_publish, context_selector, native_candidate_lifecycle
        from context_writer_lock import exclusive_writer
        operations = [lambda: refresh_graph.ensure_fresh(),
                      lambda: refresh_publish.main('/missing'),
                      lambda: context_selector.register(None, '/missing'),
                      lambda: native_candidate_lifecycle.reconcile(None, PRODUCTION_ROOT, '/missing', {}),
                      lambda: exclusive_writer(PRODUCTION_ROOT).__enter__()]
        for operation in operations:
            with self.subTest(operation=operation):
                with self.assertRaises(ProductionGraphUpdatesStopped):
                    operation()

    def test_isolated_sqlite_helper_remains_available(self):
        import refresh_facts
        with tempfile.TemporaryDirectory(dir=FIXTURE_ROOT) as directory:
            path = pathlib.Path(directory) / 'fixture.sqlite'
            require_graph_storage_write(path)
            connection = refresh_facts.connect(path)
            connection.close()
            self.assertTrue(path.exists())



class MaintenancePolicyTests(unittest.TestCase):
    def setUp(self):
        import production_write_stop as stop
        self.stop = stop
        self.directory = tempfile.TemporaryDirectory(dir=FIXTURE_ROOT)
        self.addCleanup(self.directory.cleanup)
        self.root = pathlib.Path(self.directory.name)
        self.policy = self.root / 'dependency-graph/PRODUCTION_GRAPH_STOP.json'
        self.policy.parent.mkdir()
        self.receipt = self.root / 'accepted-package.json'
        self.commit = 'a' * 40
        self.record = dict(version=1, package_scope='explicit-test-package',
                           commit=self.commit, accepted=True, committed=True)
        self.authorization = dict(version=2,
            production_graph_updates='maintenance_update',
            authority='Reviewed explicit user maintenance instruction',
            boundary=dict(receipt=dict(path='accepted-package.json', sha256=''),
                          package_scope='explicit-test-package', commit=self.commit))
        self.patcher = patch.object(stop, 'PRODUCTION_ROOT', self.root)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def save(self):
        import hashlib, json
        self.receipt.write_text(json.dumps(self.record))
        self.authorization['boundary']['receipt']['sha256'] = hashlib.sha256(
            self.receipt.read_bytes()).hexdigest()
        self.policy.write_text(json.dumps(self.authorization))

    def check_both(self, permitted=False):
        for operation in (
                lambda: self.stop.require_graph_updates(),
                lambda: self.stop.require_graph_storage_write(
                    self.root / 'dependency-graph/state/source.sqlite'),
                lambda: self.stop.require_graph_storage_write(
                    self.root / 'temp/recovery-work/dependency-graph/refresh/run/delta.sqlite')):
            with self.subTest(operation=operation, permitted=permitted):
                if permitted:
                    operation()
                else:
                    with self.assertRaises(ProductionGraphUpdatesStopped):
                        operation()

    def test_reviewed_accepted_committed_boundary_allows_both(self):
        self.save()
        self.check_both(permitted=True)
        self.assertFalse((self.root / 'dependency-graph/state').exists())

    def test_missing_malformed_unknown_policy_stays_closed(self):
        for content in (None, '{', '[]', '{}',
                        '{"version":99,"production_graph_updates":"maintenance_update"}',
                        '{"version":2,"production_graph_updates":"enabled"}'):
            if content is None:
                self.policy.unlink(missing_ok=True)
            else:
                self.policy.write_text(content)
            self.check_both()

    def test_unaccepted_or_uncommitted_or_non_boolean_receipt_stays_closed(self):
        for key, value in [('accepted', False), ('committed', False),
                           ('accepted', 1), ('committed', 'true')]:
            previous = self.record[key]
            self.record[key] = value
            self.save()
            self.check_both()
            self.record[key] = previous

    def test_missing_malformed_tampered_receipt_stays_closed(self):
        self.save()
        for content in (None, '{', '{}', '{"accepted":true}'):
            if content is None:
                self.receipt.unlink(missing_ok=True)
            else:
                self.receipt.write_text(content)
            self.check_both()

    def test_scope_commit_or_schema_mismatch_stays_closed(self):
        for key, value in [('commit', 'b' * 40),
                           ('package_scope', 'different-package'),
                           ('version', 2), ('extra', True)]:
            previous = self.record.copy()
            self.record[key] = value
            self.save()
            self.check_both()
            self.record = previous

    def test_external_or_symlinked_receipt_stays_closed(self):
        self.save()
        original = self.authorization['boundary']['receipt']['path']
        for path in (str(self.receipt.resolve()), '../outside.json'):
            self.authorization['boundary']['receipt']['path'] = path
            import json
            self.policy.write_text(json.dumps(self.authorization))
            self.check_both()
        self.authorization['boundary']['receipt']['path'] = original
        self.receipt.unlink()
        self.receipt.symlink_to('/dev/null')
        import json
        self.policy.write_text(json.dumps(self.authorization))
        self.check_both()

    def test_duplicate_keys_and_unknown_fields_never_authorize(self):
        import json
        self.save()
        data = self.policy.read_text()
        self.policy.write_text(data[:-1] + ',"version":2}')
        self.check_both()
        self.authorization['override'] = True
        self.policy.write_text(json.dumps(self.authorization))
        self.check_both()

    def test_restopping_window_blocks_again_without_touching_fixture_helpers(self):
        import json
        self.save()
        self.check_both(permitted=True)
        self.policy.write_text(json.dumps(dict(version=1,
            production_graph_updates='stopped')))
        self.check_both()
        self.stop.require_graph_storage_write(self.root / 'isolated-fixture.sqlite')

    def test_environment_never_authorizes_missing_boundary(self):
        self.save()
        self.receipt.unlink()
        with patch.dict('os.environ', {'ALLOW_GRAPH_WRITES': '1',
                                      'MEMGRAPH_URI': 'bolt://unused:7687'}):
            self.check_both()


if __name__ == '__main__':
    unittest.main()
