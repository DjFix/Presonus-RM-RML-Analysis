"""Behavioral contract for isolated compact fact stores; no operational DBs."""
import json
import sqlite3
import unittest
from unittest.mock import patch

import compact_facts
from compact_facts import CompactFacts, connect, create_schema
from refresh_facts import merged_node


def node(kind='Function', label='function', **metadata):
    return {'kind': kind, 'label': label, 'metadata': metadata}


class CompactFactsTests(unittest.TestCase):
    def setUp(self):
        self.db = connect(':memory:')
        self.addCleanup(self.db.close)
        self.store = CompactFacts(self.db)
        self.nodes = {'fn': node(mangled='_Z2fnv', source_definition=True)}
        self.edge = ('fn', 'external', 'CALLS', json.dumps({'path': 'a.cpp', 'line': 7,
                     'column': 3, 'tu': 'unit', 'context': 'compile', 'source': 'source.cpp',
                     'extra': {'anything': [1, 2, 3]}}))

    def count(self, table):
        return self.db.execute('SELECT count(*) FROM ' + table).fetchone()[0]

    def dump(self):
        return tuple(self.db.iterdump())

    def test_shared_support_and_read_only_views(self):
        first = self.store.replace_owner('a', self.nodes, [self.edge])
        second = self.store.replace_owner('b', self.nodes, [self.edge])
        edge_id = next(iter(first.changed_edges))
        self.assertEqual(second.changed_edges[edge_id].before_owners, ('a',))
        self.assertEqual(second.changed_edges[edge_id].after_owners, ('a', 'b'))
        self.assertEqual(second.changed_nodes['fn'].before[0][0], 'a')
        self.assertEqual(tuple(value[0] for value in second.changed_nodes['fn'].after), ('a', 'b'))
        self.assertEqual(self.count('compact_node_values'), 1)
        self.assertEqual(self.count('compact_logical_edges'), 1)
        self.assertEqual(self.count('compact_provenance'), 1)
        self.assertEqual(self.count('compact_edge_observations'), 1)
        self.assertEqual(self.db.execute('SELECT owner,id,kind,label,metadata FROM node_facts ORDER BY owner').fetchall(),
                         [(owner, 'fn', 'Function', 'function', json.dumps(self.nodes['fn']['metadata'], sort_keys=True))
                          for owner in ('a', 'b')])
        self.assertEqual(self.db.execute('SELECT owner,src,dst,kind,evidence FROM edge_facts ORDER BY owner').fetchall(),
                         [(owner, *self.edge) for owner in ('a', 'b')])
        with self.assertRaises(sqlite3.OperationalError):
            self.db.execute("DELETE FROM node_facts WHERE owner='a'")
        with self.assertRaises(sqlite3.OperationalError):
            self.db.execute("DELETE FROM edge_facts WHERE owner='a'")

    def test_unchanged_input_performs_zero_row_writes(self):
        self.store.replace_owner('a', self.nodes, [self.edge])
        self.db.commit()
        before = self.db.total_changes
        change = self.store.replace_owner('a', self.nodes, [self.edge, self.edge])
        self.assertEqual(change.changed_nodes, {})
        self.assertEqual(change.changed_edges, {})
        self.assertEqual(self.db.total_changes, before)
        self.store.replace_owner('unknown-empty', {}, iter(()))
        self.assertEqual(self.db.total_changes, before)
        self.db.rollback()
        self.assertEqual(self.count('node_facts'), 1)

    def test_one_provenance_change_preserves_shared_logical_edge_and_other_owner(self):
        first = self.store.replace_owner('a', self.nodes, [self.edge])
        self.store.replace_owner('b', self.nodes, [self.edge])
        changed_edge = (*self.edge[:3], self.edge[3].replace('"line": 7', '"line": 8'))
        change = self.store.replace_owner('a', self.nodes, [changed_edge])
        self.assertEqual(change.changed_nodes, {})
        self.assertEqual(len(change.changed_edges), 2)
        old = change.changed_edges[next(iter(first.changed_edges))]
        new = next(value for value in change.changed_edges.values() if value.evidence == changed_edge[3])
        self.assertEqual((old.before_owners, old.after_owners), (('a', 'b'), ('b',)))
        self.assertEqual((new.before_owners, new.after_owners), ((), ('a',)))
        self.assertEqual(old.edge_id, new.edge_id)
        self.assertEqual(self.count('compact_logical_edges'), 1)
        self.assertEqual(self.count('compact_provenance'), 2)
        self.assertEqual(self.count('edge_facts'), 2)

    def test_last_support_removal_and_explicit_touched_pruning(self):
        added = self.store.replace_owner('a', self.nodes, [self.edge])
        removed = self.store.replace_owner('a', {}, [])
        self.assertEqual(removed.changed_nodes['fn'].after, ())
        observation_id = next(iter(added.changed_edges))
        self.assertEqual(removed.changed_edges[observation_id].after_owners, ())
        self.assertEqual(self.count('node_facts'), 0)
        self.assertEqual(self.count('edge_facts'), 0)
        # Delta consumers can still resolve IDs until explicit pruning.
        self.assertEqual(self.count('compact_edge_observations'), 1)
        self.assertEqual(removed.changed_edges[observation_id].src, 'fn')
        self.store.prune_unreferenced([added, removed])
        for table in ('compact_node_keys', 'compact_owners', 'compact_node_values', 'compact_kinds',
                      'compact_logical_edges', 'compact_provenance', 'compact_edge_observations', 'compact_atoms'):
            self.assertEqual(self.count(table), 0, table)

    def test_prune_respects_other_owners_and_unrelated_orphans(self):
        self.store.replace_owner('historical', {'old': node(label='old')}, [('old', 'other', 'OLD', 'legacy')])
        self.store.replace_owner('historical', {}, [])
        self.store.replace_owner('a', self.nodes, [self.edge])
        self.store.replace_owner('b', self.nodes, [self.edge])
        removed = self.store.replace_owner('a', {}, [])
        self.store.prune_unreferenced(removed)
        self.assertEqual(self.count('node_facts'), 1)
        self.assertEqual(self.count('edge_facts'), 1)
        self.assertEqual(self.count('compact_logical_edges'), 2)
        self.assertEqual(self.count('compact_node_values'), 2)
        self.assertEqual(self.count('compact_provenance'), 2)
        self.assertEqual(self.db.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_conflicting_kind_fails_atomically_and_own_kind_can_change(self):
        self.store.replace_owner('a', self.nodes, [self.edge])
        before = self.dump()
        with self.assertRaisesRegex(ValueError, 'Conflicting node kinds for fn'):
            self.store.replace_owner('b', {'new-key': node(label='new'), 'fn': node('Data')}, [])
        self.assertEqual(self.dump(), before)
        self.store.replace_owner('a', {'fn': node('Data')}, [self.edge])
        self.assertEqual(self.db.execute('SELECT kind FROM node_facts').fetchone()[0], 'Data')

    def test_caller_rollback_restores_complete_previous_state(self):
        self.store.replace_owner('a', self.nodes, [self.edge])
        self.db.commit()
        before = self.dump()
        self.store.replace_owner('a', {'replacement': node(label='new')}, [('replacement', 'new', 'NEXT', 'new evidence')])
        self.assertTrue(self.db.in_transaction)
        self.db.rollback()
        self.assertEqual(self.dump(), before)
        self.store.replace_owner('a', {}, [])
        change = self.store.replace_owner('a', {}, [])
        self.assertEqual(change.changed_nodes, {})
        self.db.rollback()
        self.assertEqual(self.dump(), before)

    def test_merged_node_owner_order_and_boolean_fold_match_legacy_consumer(self):
        self.store.replace_owner('z', {'fn': node(label='last', source_definition=False, value='z')}, [])
        self.store.replace_owner('a', {'fn': node(label='first', source_definition=True, value='a')}, [])
        merged = merged_node(self.db, 'fn')
        self.assertEqual(merged['label'], 'last')
        self.assertEqual(json.loads(merged['metadata']), {'source_definition': True, 'value': 'z'})
        before = self.db.total_changes
        self.store.replace_owner('a', {'fn': node(label='first', value='a', source_definition=True)}, [])
        self.assertEqual(self.db.total_changes, before)

    def test_provenance_is_decomposed_and_raw_shared_without_broad_indexes(self):
        self.store.replace_owner('a', self.nodes, [self.edge, ('fn', 'other', 'CALLS', self.edge[3])])
        self.assertEqual(self.count('compact_logical_edges'), 2)
        self.assertEqual(self.count('compact_provenance'), 1)
        row = self.db.execute('''SELECT p.raw_evidence,a.value,p.line,p.column_number,t.value,c.value,s.value
            FROM compact_provenance p JOIN compact_atoms a ON a.atom_id=p.path_id
            JOIN compact_atoms t ON t.atom_id=p.tu_id JOIN compact_atoms c ON c.atom_id=p.context_id
            JOIN compact_atoms s ON s.atom_id=p.source_id''').fetchone()
        self.assertEqual(row, (self.edge[3], 'a.cpp', 7, 3, 'unit', 'compile', 'source.cpp'))
        for table in ('compact_node_memberships', 'compact_edge_memberships'):
            schema = self.db.execute('SELECT sql FROM sqlite_master WHERE name=?', (table,)).fetchone()[0]
            self.assertIn('WITHOUT ROWID', schema)
            self.assertTrue(all(row[2] == 'INTEGER' for row in self.db.execute('PRAGMA table_info(' + table + ')')))
        for table in ('compact_node_values', 'compact_provenance'):
            columns = {row[2] for index in self.db.execute('PRAGMA index_list(' + table + ')')
                       for row in self.db.execute('PRAGMA index_info(' + index[1] + ')')}
            self.assertIn('fingerprint', columns)
            self.assertNotIn('metadata', columns)
            self.assertNotIn('raw_evidence', columns)
            self.assertNotIn('label', columns)

    def test_raw_evidence_whitespace_is_preserved_and_extras_do_not_expand_indexes(self):
        other = (*self.edge[:3], json.dumps(json.loads(self.edge[3]), separators=(',', ':')))
        self.store.replace_owner('a', self.nodes, [self.edge, other])
        self.assertEqual(self.count('compact_logical_edges'), 1)
        self.assertEqual(self.count('compact_provenance'), 2)
        self.assertEqual({row[0] for row in self.db.execute('SELECT evidence FROM edge_facts')}, {self.edge[3], other[3]})

    def test_hash_collisions_do_not_merge_distinct_values_or_evidence(self):
        class ConstantHash:
            def digest(self):
                return b'x' * 32
        with patch.object(compact_facts.hashlib, 'sha256', return_value=ConstantHash()):
            self.store.replace_owner('a', {'one': node(label='one'), 'two': node(label='two')},
                                     [('one', 'two', 'CALLS', 'one'), ('one', 'two', 'CALLS', 'two')])
            self.assertEqual(self.count('compact_node_values'), 2)
            self.assertEqual(self.count('compact_provenance'), 2)
            before = self.db.total_changes
            self.store.replace_owner('a', {'one': node(label='one'), 'two': node(label='two')},
                                     [('one', 'two', 'CALLS', 'one'), ('one', 'two', 'CALLS', 'two')])
            self.assertEqual(self.db.total_changes, before)

    def test_pruning_remains_inside_caller_rollback(self):
        self.store.replace_owner('a', self.nodes, [self.edge])
        self.db.commit()
        before = self.dump()
        removed = self.store.replace_owner('a', {}, [])
        self.store.prune_unreferenced(removed)
        self.assertEqual(self.count('compact_node_values'), 0)
        self.assertTrue(self.db.in_transaction)
        self.db.rollback()
        self.assertEqual(self.dump(), before)

    def test_failed_replace_preserves_prior_uncommitted_owner_work(self):
        self.store.replace_owner('a', self.nodes, [self.edge])
        before = self.dump()
        with self.assertRaises(ValueError):
            self.store.replace_owner('b', {'temporary': node()}, [('temporary', 'fn', 'CALLS', 123)])
        self.assertEqual(self.dump(), before)
        self.assertTrue(self.db.in_transaction)
        self.db.commit()
        self.assertEqual(self.count('node_facts'), 1)

    def test_import_many_shared_owners_never_materializes_support(self):
        with patch.object(self.store, '_node_support', side_effect=AssertionError('support scan')), \
                patch.object(self.store, '_edge_support', side_effect=AssertionError('support scan')):
            for owner in range(40):
                result = self.store.import_owner(str(owner),
                    (('fn' + str(i), node(label='shared')) for i in range(50)),
                    (('fn' + str(i), 'target', 'CALLS', 'shared evidence') for i in range(50)))
                self.assertEqual(result, {'nodes': 50, 'edges': 50})
            before = self.dump()
            with self.assertRaisesRegex(ValueError, 'Conflicting node kinds'):
                self.store.import_owner('conflict', [('fn0', node('Data'))], [])
            self.assertEqual(self.dump(), before)
        self.assertEqual(self.count('node_facts'), 2000)
        self.assertEqual(self.count('edge_facts'), 2000)
        self.assertEqual(self.count('compact_node_values'), 1)
        self.assertEqual(self.count('compact_provenance'), 1)
        self.assertIsNone(self.store._import_cache)

    def test_import_streams_bounded_batches_and_refuses_nonempty_owner(self):
        def nodes():
            for i in range(140):
                if i == 64:
                    self.assertEqual(self.count('compact_node_memberships'), 64)
                yield 'node' + str(i), node()
        def edges():
            for i in range(140):
                if i == 64:
                    self.assertEqual(self.count('compact_edge_memberships'), 64)
                yield 'node' + str(i), 'target', 'CALLS', 'evidence'
        self.assertEqual(self.store.import_owner('a', nodes(), edges(), batch_size=64), {'nodes': 140, 'edges': 140})
        before = self.dump()
        with self.assertRaisesRegex(ValueError, 'not empty'):
            self.store.import_owner('a', {}, [])
        self.assertEqual(self.dump(), before)
        self.db.rollback()
        self.assertEqual(self.store.import_owner('a', self.nodes, [self.edge]), {'nodes': 1, 'edges': 1})

    def test_import_rollback_and_prune_cannot_reuse_stale_cache_ids(self):
        self.store.import_owner('a', self.nodes, [self.edge])
        self.db.rollback()
        self.assertEqual(self.store.import_owner('other', {'different': node('Data')}, []), {'nodes': 1, 'edges': 0})
        self.store.import_owner('a', self.nodes, [self.edge])
        change = self.store.replace_owner('a', {}, [])
        self.store.prune_unreferenced(change)
        self.assertEqual(self.store.import_owner('a', self.nodes, [self.edge]), {'nodes': 1, 'edges': 1})
        self.assertEqual(self.db.execute('PRAGMA foreign_key_check').fetchall(), [])
        self.assertIsNone(self.store._import_cache)

    def test_import_cache_enforces_entry_and_byte_limits(self):
        cache = compact_facts._ImportCache(max_entries=3, max_bytes=1024)
        cache.put(('oversized', 'x' * 2048), 1)
        self.assertIsNone(cache.get(('oversized', 'x' * 2048)))
        for i in range(100):
            cache.put(('key', str(i)), i)
            self.assertLessEqual(len(cache.entries), 3)
            self.assertLessEqual(cache.bytes, 1024)

    def test_unchanged_memberships_skip_kind_representative_query(self):
        for owner in ('a', 'b', 'c'):
            self.store.import_owner(owner, self.nodes, [self.edge])
        trace = []
        self.db.set_trace_callback(trace.append)
        self.store.replace_owner('a', self.nodes, [self.edge])
        self.db.set_trace_callback(None)
        self.assertFalse(any('SELECT v.kind_id FROM compact_node_memberships' in query for query in trace))
        for owner, kind in (('d', 'Data'),):
            with self.assertRaisesRegex(ValueError, 'Conflicting node kinds'):
                self.store.replace_owner(owner, {'fn': node(kind)}, [])

    def test_sqlite_auto_rollback_preserves_original_interrupt(self):
        for operation in ('replace_owner', 'import_owner'):
            self.db.commit()
            def interrupted_write(key):
                calls = [0]
                def abort_after_compilation():
                    calls[0] += 1
                    return int(calls[0] >= 50)
                self.db.set_progress_handler(abort_after_compilation, 1)
                # A write interrupted inside SQLite rolls back the whole outer
                # transaction, removing our savepoint before API cleanup runs.
                self.db.execute("INSERT INTO compact_node_keys(value) SELECT 'abort:' || value FROM json_each(?)",
                                (json.dumps(list(range(100))),))
            try:
                with patch.object(self.store, '_node_key', side_effect=interrupted_write):
                    with self.assertRaisesRegex(sqlite3.OperationalError, '^interrupted$'):
                        getattr(self.store, operation)('interrupted', self.nodes, [self.edge])
            finally:
                self.db.set_progress_handler(None, 0)
            self.assertFalse(self.db.in_transaction)
            self.assertEqual(self.count('node_facts'), 0)
            self.assertIsNone(self.store._import_cache)

    def test_schema_rejects_legacy_tables_without_implicit_migration(self):
        db = sqlite3.connect(':memory:')
        self.addCleanup(db.close)
        db.execute('CREATE TABLE node_facts(owner,id,kind,label,metadata)')
        before = tuple(db.iterdump())
        with self.assertRaisesRegex(ValueError, 'explicit staging migration'):
            create_schema(db)
        self.assertEqual(tuple(db.iterdump()), before)

    def test_schema_creation_preserves_callers_existing_transaction(self):
        db = sqlite3.connect(':memory:')
        self.addCleanup(db.close)
        db.execute('CREATE TABLE meta(key,value)')
        db.execute("INSERT INTO meta VALUES('existing','uncommitted')")
        create_schema(db)
        self.assertTrue(db.in_transaction)
        db.rollback()
        self.assertEqual(db.execute('SELECT * FROM meta').fetchall(), [])
        self.assertFalse(db.execute("SELECT 1 FROM sqlite_master WHERE name='compact_owners'").fetchall())


if __name__ == '__main__':
    unittest.main()
