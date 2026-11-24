"""Offline regressions: never create a driver or touch production storage."""
import pathlib
import tempfile
import sys
import types
import unittest
from unittest.mock import patch

from production_write_stop import (PRODUCTION_ROOT, ProductionGraphUpdatesStopped,
                                   require_graph_updates, require_graph_storage_write)


class StopTests(unittest.TestCase):
    def test_canonical_cannot_be_reopened_by_environment_or_removed_policy(self):
        with patch.dict('os.environ', {'ALLOW_GRAPH_WRITES': '1', 'MEMGRAPH_URI': 'bolt://unused:7687'}):
            with patch.object(pathlib.Path, 'exists', return_value=False):
                with self.assertRaises(ProductionGraphUpdatesStopped):
                    require_graph_updates(PRODUCTION_ROOT)

    def test_copy_policy_is_stopped_and_fixture_root_allowed(self):
        with tempfile.TemporaryDirectory() as directory:
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
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / 'fixture.sqlite'
            require_graph_storage_write(path)
            connection = refresh_facts.connect(path)
            connection.close()
            self.assertTrue(path.exists())


if __name__ == '__main__':
    unittest.main()
