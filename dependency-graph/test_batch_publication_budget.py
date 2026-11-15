"""Offline publisher budget and compact-view resume regression checks."""
import io
import json
import sqlite3
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from batch_publication import BudgetedRequests, publish, _RequestShapeRecorder
from context_runtime import ContextError
from publication_budget import BudgetExceeded, BudgetLimits, PublicationBudget


class Result(list):
    def single(self):
        return self[0] if self else None
    def consume(self):
        return None


class FakeBolt:
    def __init__(self):
        self.calls = []
        self.state = dict(phase=0, last_row=0, commits=0, verified=0)
        self.committed_cursors = []
        self.pending = None
    def run(self, query, **params):
        self.calls.append((query, params))
        if 'p.digest AS digest' in query:
            return Result([dict(digest='digest', batch_size=1)])
        if 'RETURN p.phase AS phase' in query:
            return Result([dict(self.state)])
        if 'SET p.phase=$next_phase' in query:
            if (self.state['phase'], self.state['last_row']) != (params['phase'], params['last']):
                return Result([{'n': 0}])
            self.pending = dict(phase=params['next_phase'], last_row=params['next_row'],
                                commits=self.state['commits'] + 1, verified=self.state['verified'])
            return Result([{'n': 1}])
        if 'MERGE(s)-[:' in query:
            return Result([{'n': len(params['rows'])}])
        if 'DELETE r' in query:
            return Result()
        raise AssertionError(query)
    def begin_transaction(self):
        return self
    def __enter__(self):
        return self
    def __exit__(self, kind, value, traceback):
        self.pending = None
    def commit(self):
        if self.pending:
            self.state = self.pending
            self.committed_cursors.append((self.state['phase'], self.state['last_row']))
            self.pending = None


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
            CREATE TABLE settings(key,value);
            INSERT INTO settings VALUES('replace_legacy_build',0);
            CREATE TABLE nodes(id,kind,label,metadata);
            CREATE TABLE orphan_nodes(id);
            CREATE TABLE effects(id INTEGER PRIMARY KEY,operation,src,dst,kind,evidence);
            INSERT INTO effects VALUES(7,-1,'a','b','CALLS','raw');
            INSERT INTO effects VALUES(9,1,'a','c','CALLS','é');
            CREATE VIEW old_edges AS SELECT id AS rowid,src,dst,kind,evidence FROM effects WHERE operation=-1;
            CREATE VIEW new_edges AS SELECT id AS rowid,src,dst,kind,evidence FROM effects WHERE operation=1;
            CREATE VIEW prior_edges AS SELECT * FROM old_edges WHERE 0;
        ''')
        self.patches = [patch('batch_publication.sha', return_value='digest'),
                        patch('batch_publication.pathlib.Path.stat', return_value=SimpleNamespace(st_size=4096)),
                        patch('batch_publication.pathlib.Path.open', side_effect=lambda *a, **k: io.StringIO()),
                        patch('batch_publication.pathlib.Path.write_text')]
        self.mocks = [p.start() for p in self.patches]
    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.db.close()
    def budget(self, **limits):
        return PublicationBudget(BudgetLimits(**limits), io_reader=lambda: 0)
    def verified(self, session, db, checkpoint):
        if isinstance(session, _RequestShapeRecorder):
            from publication_events import verify_pending
            return verify_pending(session, db, checkpoint)
        session.target.state['verified'] = session.target.state['commits']
        return None

    def test_journal_budget_rejects_before_any_request(self):
        server = FakeBolt()
        with self.assertRaises(BudgetExceeded):
            publish(server, self.db, 'delta.sqlite', 'commits.jsonl', budget=self.budget(journal_bytes=1))
        self.assertEqual(server.calls, [])
        receipt = json.loads(self.mocks[-1].call_args.args[0])
        self.assertIn('budget exceeded', receipt['publication_failure'])

    def test_transfer_estimate_rejects_before_any_request(self):
        server = FakeBolt()
        with self.assertRaises(BudgetExceeded):
            publish(server, self.db, 'delta.sqlite', 'commits.jsonl', budget=self.budget(transfer_bytes=1))
        self.assertEqual(server.calls, [])

    def test_request_charge_precedes_mutation_and_counts_utf8_json(self):
        budget = self.budget(transfer_bytes=1000)
        budget.preflight(journal_estimate_bytes=0, sqlite_write_estimate_bytes=0, rows=0, transfer_bytes=0)
        server = FakeBolt()
        wrapped = BudgetedRequests(server, budget)
        query = 'DELETE r'
        wrapped.run(query, text='é')
        expected = json.dumps({'query': query, 'parameters': {'text': 'é'}}, ensure_ascii=False,
                              sort_keys=True, separators=(',', ':')).encode()
        self.assertEqual(budget.transfer_bytes, len(expected))
        small = self.budget(transfer_bytes=1)
        small.preflight(journal_estimate_bytes=0, sqlite_write_estimate_bytes=0, rows=0, transfer_bytes=0)
        with self.assertRaises(BudgetExceeded):
            BudgetedRequests(server, small).run(query, text='é')
        self.assertEqual(len(server.calls), 1)

    def test_compact_sparse_cursors_survive_interruption(self):
        server = FakeBolt()
        with patch('batch_publication.verify_pending', side_effect=self.verified):
            with self.assertRaisesRegex(ContextError, 'Injected interruption'):
                publish(server, self.db, 'delta.sqlite', 'commits.jsonl', batch_size=1,
                        stop_after=2, budget=self.budget())
            self.assertEqual((server.state['phase'], server.state['last_row']), (1, 7))
            receipt = publish(server, self.db, 'delta.sqlite', 'commits.jsonl', batch_size=1,
                              budget=self.budget())
        self.assertEqual(server.state['phase'], 4)
        self.assertEqual(receipt['verification_state'], 'verified')
        deleted = [params['rows'][0]['journal_row'] for query, params in server.calls if 'DELETE r' in query]
        self.assertEqual(deleted, [7])
        self.assertIn((2, 9), server.committed_cursors)
        budget_receipt = json.loads(self.mocks[-1].call_args.args[0])
        self.assertIn('not Bolt wire bytes', budget_receipt['transfer_measurement'])
        self.assertEqual(budget_receipt['publication_preflight']['emitted_rows'], 2)
        self.assertEqual(self.mocks[-1].call_count, 2)  # Once per invocation.

    def test_kind_change_still_fails_before_node_mutation(self):
        from batch_publication import apply_rows
        class ExistingKind:
            def __init__(self):
                self.calls = []
            def run(self, query, **params):
                self.calls.append(query)
                return Result([{'id': 'compiler:c:1', 'kind': 'Function',
                                'wanted': 'Data', 'labels': ['Artifact', 'Function']}])
        target = ExistingKind()
        budget = self.budget()
        budget.preflight(journal_estimate_bytes=0, sqlite_write_estimate_bytes=0, rows=0, transfer_bytes=0)
        with self.assertRaisesRegex(ContextError, 'reviewed migration'):
            apply_rows(BudgetedRequests(target, budget), 'nodes',
                       [{'id': 'compiler:c:1', 'kind': 'Data', 'label': 'x', 'metadata': '{}'}])
        self.assertEqual(len(target.calls), 1)
        self.assertNotIn('MERGE', target.calls[0])

    def test_rows_charged_before_apply(self):
        server = FakeBolt()
        budget = self.budget()
        from batch_publication import apply_rows
        def check(tx, phase, rows):
            if not isinstance(tx, _RequestShapeRecorder):
                self.assertGreaterEqual(budget.rows, len(rows))
            return apply_rows(tx, phase, rows)
        with patch('batch_publication.verify_pending', side_effect=self.verified), \
             patch('batch_publication.apply_rows', side_effect=check):
            publish(server, self.db, 'delta.sqlite', 'commits.jsonl', batch_size=1, budget=budget)
        self.assertEqual(budget.rows, 2)

    def test_planner_counts_real_apply_and_verification_shapes_for_wide_utf8(self):
        import batch_publication as publisher
        meta = json.dumps({'path': 'é/' + 'x' * 4000, 'mangled': '_ZN1A1fEv'}, ensure_ascii=False)
        self.db.executemany('INSERT INTO nodes VALUES(?,?,?,?)',
                            [('a', 'Function', 'A', meta), ('b', 'Data', 'B', meta),
                             ('c', 'file', 'C', '{}')])
        self.db.execute("INSERT INTO orphan_nodes VALUES('gone')")
        captured = []
        class Recorder(_RequestShapeRecorder):
            def count(self, query, parameters):
                captured.append(json.loads(publisher.request_envelope(query, parameters)))
                return super().count(query, parameters)
        budget = self.budget()
        with patch.object(publisher, '_RequestShapeRecorder', Recorder):
            plan = publisher.journal_preflight(self.db, 'delta.sqlite', budget, 2)
        self.assertEqual(plan['emitted_rows'], 6)
        self.assertEqual(plan['json_request_estimate_bytes'],
                         sum(len(publisher.request_envelope(x['query'], x['parameters'])) for x in captured))
        self.assertEqual(plan['planned_json_requests'], len(captured))
        self.assertEqual(budget.transfer_bytes, 0)  # Planning does not claim requests were sent.
        apply = [x for x in captured if 'MERGE(n:Artifact' in x['query']]
        self.assertEqual(len(apply), 3)  # Real per-kind grouping across two node batches.
        self.assertEqual(apply[0]['parameters']['rows'][0]['mangled'], '_ZN1A1fEv')
        verify = [x for x in captured if 'properties(n) AS props' in x['query']]
        self.assertEqual(len(verify), 2)
        self.assertNotIn('mangled', verify[0]['parameters']['rows'][0])
        self.assertTrue(any('count(r) AS n' in x['query'] for x in captured))
        self.assertTrue(any('count(DISTINCT n)' in x['query'] for x in captured))
        self.assertEqual(plan['phases']['nodes']['rows'], 3)
        self.assertEqual(plan['phases']['orphan_nodes']['rows'], 1)
        # A multiplier would charge the wide metadata many times beyond the
        # actual lookup/apply/verification envelopes and reject a valid cap.
        old_estimate = 65536 + plan['encoded_row_bytes'] * 16 + plan['emitted_rows'] * 1024 + 3 * 16384
        self.assertGreater(old_estimate, plan['json_request_estimate_bytes'] * 2)
        exact = plan['json_request_estimate_bytes']
        publisher.journal_preflight(self.db, 'delta.sqlite', self.budget(transfer_bytes=exact), 2)
        with self.assertRaises(BudgetExceeded):
            publisher.journal_preflight(self.db, 'delta.sqlite', self.budget(transfer_bytes=exact-1), 2)

    def test_planning_keeps_immutable_rows_and_no_verification_receipt(self):
        from batch_publication import journal_preflight
        self.db.execute('INSERT INTO nodes VALUES(?,?,?,?)',
                        ('a', 'Function', 'a', '{"mangled":"_Z1fv","path":"a.cpp"}'))
        before = tuple(self.db.iterdump())
        plan = journal_preflight(self.db, 'delta.sqlite', self.budget(), 1)
        self.assertEqual(tuple(self.db.iterdump()), before)
        self.assertNotIn('verification_state', plan)
        self.assertNotIn('verification_contract', plan)
        self.assertIn('not execution evidence', plan['planning_scope'])


if __name__ == '__main__':
    unittest.main()
