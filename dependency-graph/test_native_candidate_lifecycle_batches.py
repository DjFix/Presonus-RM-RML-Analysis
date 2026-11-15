"""Offline regression checks for physical uniqueness and bounded orphan reads."""
import inspect
import unittest
from unittest.mock import patch

from context_runtime import ContextError
from native_candidate_gate import BATCH_SIZE
from native_candidate_lifecycle import orphan_snapshots, reconcile, verify_scope


class Session:
    def __init__(self, nodes):
        self.nodes = nodes
        self.calls = []

    def run(self, query, **params):
        self.calls.append((query, params))
        if query == 'MATCH(n) WHERE n.id IN $ids RETURN n.id AS identity':
            return [{'identity': n['id']} for n in self.nodes if n['id'] in params['ids']]
        if query.startswith('UNWIND $ids AS key MATCH(n:Artifact {id:key}) '):
            return [{'identity': n['id'], 'physical': i, 'props': {'id': n['id']},
                     'labels': n['labels'], 'degree': n.get('degree', 0)}
                    for i, n in enumerate(self.nodes)
                    if n['id'] in params['ids'] and 'Artifact' in n['labels']]
        raise AssertionError(query)


class OrphanBatches(unittest.TestCase):
    def test_cross_label_duplicate_is_rejected(self):
        session = Session([{'id': 'a', 'labels': ['Artifact']},
                           {'id': 'a', 'labels': ['Other']}])
        with self.assertRaisesRegex(ContextError, 'Duplicate lifecycle orphan identity'):
            orphan_snapshots(session, ['a'])

    def test_wrong_label_singleton_is_rejected(self):
        with self.assertRaisesRegex(ContextError, 'not an Artifact'):
            orphan_snapshots(Session([{'id': 'a', 'labels': ['Other']}]), ['a'])

    def test_missing_and_connected_orphans(self):
        session = Session([{'id': 'connected', 'labels': ['Extra', 'Artifact'], 'degree': 2}])
        missing, connected = orphan_snapshots(session, ['missing', 'connected'])
        self.assertEqual(missing, ({'id': 'missing', 'node': None}, None))
        self.assertEqual(connected[1], 2)
        self.assertEqual(connected[0]['node']['labels'], ['Artifact', 'Extra'])

    def test_after_snapshot_independently_observes_deletion(self):
        session = Session([{'id': 'a', 'labels': ['Artifact']}])
        before = orphan_snapshots(session, ['a'])
        session.nodes.clear()
        after = orphan_snapshots(session, ['a'])
        self.assertIsNotNone(before[0][0]['node'])
        self.assertEqual(after, [({'id': 'a', 'node': None}, None)])
        self.assertEqual(sum(q == 'MATCH(n) WHERE n.id IN $ids RETURN n.id AS identity' for q, _ in session.calls), 2)

    def test_unrelated_identities_are_filtered_before_transfer(self):
        session = Session([{'id': str(i), 'labels': ['Artifact']} for i in range(1000)])
        self.assertEqual(len(orphan_snapshots(session, ['17'])), 1)
        query, params = session.calls[0]
        self.assertIn('WHERE n.id IN $ids', query)
        self.assertEqual(params['ids'], ['17'])

    def test_bounded_indexed_reads_and_single_inventory(self):
        ids = [str(i) for i in range(2 * BATCH_SIZE + 1)]
        session = Session([{'id': key, 'labels': ['Artifact']} for key in ids])
        self.assertEqual(len(orphan_snapshots(session, ids)), len(ids))
        self.assertEqual(len(session.calls), 4)
        for query, params in session.calls[1:]:
            self.assertIn('MATCH(n:Artifact {id:key})', query)
            self.assertLessEqual(len(params['ids']), BATCH_SIZE)
            self.assertNotIn('MATCH(n {id:', query)

    def test_empty_scope_has_no_queries(self):
        session = Session([])
        self.assertEqual(orphan_snapshots(session, []), [])
        self.assertEqual(session.calls, [])

    def test_duplicate_scope_rejected(self):
        with self.assertRaisesRegex(ContextError, 'Duplicate lifecycle orphan scope'):
            orphan_snapshots(Session([]), ['a', 'a'])

    def test_verify_scope_reads_all_orphans_together(self):
        import native_candidate_lifecycle as module
        wanted = [{'id': 'a', 'node': None}, {'id': 'b', 'node': None}]
        seal = {'version': 1, 'seal_sha256': 'seal', 'native': {'sha256': 'native'}, 'affected_ids': []}
        import json
        p = {'source_delta_sha256': 'delta', 'seal_sha256': 'seal',
             'native_generation': 'native', 'seal_json': '{}', 'state': 'verified',
             'orphan_after_json': json.dumps(wanted)}
        with patch('native_candidate_gate.verify_guard_inputs'), patch.object(module, 'sha', return_value='delta'), \
             patch.object(module, 'source_complete'), patch.object(module, 'read_checkpoint', return_value=(p, [], [], {})), \
             patch.object(module, 'OwnershipVerification'), patch.object(module, 'canonical_matches', return_value=True), \
             patch.object(module, 'scope_edges', return_value=[]), \
             patch.object(module, 'orphan_snapshots', return_value=[(x, None) for x in wanted]) as snapshots:
            verify_scope(object(), '.', 'delta', seal, 'checkpoint')
            self.assertEqual(snapshots.call_count, 1)
            self.assertEqual(list(snapshots.call_args.args[1]), ['a', 'b'])

    def test_atomic_deletion_guard_preserved(self):
        source = inspect.getsource(reconcile)
        self.assertIn('with session.begin_transaction() as tx:', source)
        self.assertIn("snapshot['node'] is not None and degree == 0", source)
        self.assertIn('MATCH(n:Artifact {id:$id}) WHERE NOT(n)--() DELETE n RETURN count(n) AS n', source)
        self.assertIn("if n != 1:", source)
        self.assertEqual(source.count('orphan_snapshots(tx, orphan_ids)'), 2)


if __name__ == '__main__':
    unittest.main()
