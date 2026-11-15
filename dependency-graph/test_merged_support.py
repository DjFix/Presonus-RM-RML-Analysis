"""Opt-in staging summaries preserve full-support semantics without histories."""
import json
import sqlite3
import unittest
from unittest.mock import patch

from compact_facts import CompactFacts, PruneCandidates, create_schema
from incremental_delta import NetChanges
from incremental_stage import IncrementalStage
from publication_budget import PublicationBudget


def node(label='same', **metadata):
    return dict(kind='Function', label=label, metadata=metadata)


class MergedSupportTests(unittest.TestCase):
    def database(self):
        c = sqlite3.connect(':memory:')
        self.addCleanup(c.close)
        create_schema(c)
        c.execute('CREATE TABLE unit_observations(owner TEXT PRIMARY KEY,observation_id TEXT,payload TEXT)')
        return c, CompactFacts(c)

    def test_full_and_merged_paths_have_identical_net_effects_and_pruning(self):
        full_db, full = self.database()
        merged_db, merged = self.database()
        full_net, merged_net = NetChanges(), NetChanges()
        histories, touched = [], PruneCandidates()
        edge = ('n', 'other', 'CALLS', '{"path":"same.cpp","line":7}')
        # Include unrelated historical orphans: neither path may sweep them.
        for store in (full, merged):
            store.replace_owner('history', {'untouched': node()}, [('untouched', 'past', 'OLD', 'history')])
            store.replace_owner('history', {}, [])
        steps = [
            ('z', {'n': node('last', value='z', source_definition=False)}, [edge]),
            ('a', {'n': node('first', value='a', source_definition=True, compiler_definition=True)}, [edge]),
            ('z', {'n': node('new-last', value=None, source_definition=False)}, [edge]),
            ('a', {}, []),
            ('z', {}, []),
            ('new', {'n': node('new', value='new')}, [edge]),
        ]
        for owner, nodes, edges in steps:
            original = full.replace_owner(owner, nodes, edges)
            summary = merged.replace_owner(owner, nodes, edges, merged=True)
            full_net.add(original)
            merged_net.add_merged(summary)
            histories.append(original)
            touched.add(summary.prune)
            self.assertEqual(full_net.nodes, merged_net.nodes)
            self.assertEqual(full_net.edges, merged_net.edges)
            for table in ('node_facts', 'edge_facts'):
                self.assertEqual(sorted(full_db.execute('SELECT * FROM ' + table)),
                                 sorted(merged_db.execute('SELECT * FROM ' + table)))
        for net in (full_net, merged_net):
            delta = sqlite3.connect(':memory:')
            self.addCleanup(delta.close)
            delta.execute('BEGIN')
            net.write(delta)
            if net is full_net:
                expected = {name: list(delta.execute('SELECT * FROM ' + name))
                            for name in ('nodes', 'orphan_nodes', 'old_edges', 'new_edges', 'changed_nodes')}
            else:
                for name, rows in expected.items():
                    self.assertEqual(list(delta.execute('SELECT * FROM ' + name)), rows)
        self.assertEqual(full.prune_unreferenced(histories), merged.prune_unreferenced(touched))
        self.assertTrue(merged_db.execute('SELECT 1 FROM compact_node_keys WHERE value="untouched"').fetchone())

    def test_merge_preserves_owner_precedence_and_boolean_or(self):
        c, store = self.database()
        store.import_owner('z', {'n': node('last', value='z', source_definition=False)}, [])
        summary = store.replace_owner('a', {'n': node('first', value='a', source_definition=True)}, [], merged=True)
        after = summary.changed_nodes['n'].after
        self.assertEqual(after['label'], 'last')
        self.assertEqual(json.loads(after['metadata']), {'value': 'z', 'source_definition': True})
        self.assertEqual(summary.prune.owners, {'a'})

    def test_repeated_values_keep_last_owner_order_with_none_and_or_fields(self):
        c, store = self.database()
        a = node('A', x=1, y=None, source_definition=True)
        b = node('B', x=2, y=3, source_definition=False)
        for owner, value in (('a', a), ('b', b), ('c', a)):
            store.import_owner(owner, {'n': value}, [])
        summary = store.replace_owner('z', {'n': b}, [], merged=True)
        before = summary.changed_nodes['n'].before
        self.assertEqual(before['label'], 'A')
        self.assertEqual(json.loads(before['metadata']), {'x': 1, 'y': 3, 'source_definition': True})
        after = summary.changed_nodes['n'].after
        self.assertEqual(after['label'], 'B')
        self.assertEqual(json.loads(after['metadata']), {'x': 2, 'y': 3, 'source_definition': True})

    def test_or_preserves_first_truthy_json_type_for_legacy_metadata(self):
        c, store = self.database()
        for owner, value in (('a', 1), ('b', True), ('c', 1)):
            store.import_owner(owner, {'n': node(source_definition=value)}, [])
        summary = store.replace_owner('z', {'n': node(source_definition=False)}, [], merged=True)
        before = json.loads(summary.changed_nodes['n'].before['metadata'])['source_definition']
        self.assertIs(type(before), int)
        self.assertEqual(before, 1)

    def test_kind_conflict_rolls_back_opt_in_interning(self):
        c, store = self.database()
        store.import_owner('a', {'n': node()}, [])
        before = list(c.execute('SELECT * FROM node_facts'))
        with self.assertRaisesRegex(ValueError, 'Conflicting node kinds'):
            store.replace_owner('b', {'new': node(), 'n': dict(kind='Data', label='data', metadata={})}, [], merged=True)
        self.assertEqual(list(c.execute('SELECT * FROM node_facts')), before)
        self.assertIsNone(c.execute('SELECT 1 FROM compact_node_keys WHERE value="new"').fetchone())

    def test_many_shared_owners_never_materialize_support_histories_in_stage(self):
        c, store = self.database()
        shared = {str(i): node(payload='x' * 1024) for i in range(24)}
        edge = ('0', '1', 'CALLS', 'exact evidence')
        for index in range(100):
            store.import_owner('owner-' + str(index).zfill(3), shared, [edge])
        stage = IncrementalStage(c, PublicationBudget(io_reader=lambda: 0))
        with (patch.object(CompactFacts, '_node_support', side_effect=AssertionError('full support tuple')),
              patch.object(CompactFacts, '_edge_support', side_effect=AssertionError('full edge owner tuple'))):
            change = stage.replace_facts('owner-050', {}, [])
        self.assertEqual(stage.net.edges[edge], (True, True))
        self.assertEqual(len(stage.prune_candidates.nodes), 24)
        self.assertEqual(stage.prune_candidates.owners, {'owner-050'})
        self.assertFalse(hasattr(stage, 'changes'))
        self.assertLess(len(repr(change)), 100000)
        self.assertTrue(all(not hasattr(value, 'before_owners') for value in change.changed_edges.values()))
        delta = sqlite3.connect(':memory:')
        self.addCleanup(delta.close)
        delta.execute('BEGIN')
        self.assertEqual(stage.finish(delta)['old_edges'], 0)
        self.assertEqual(c.execute('SELECT count(*) FROM compact_edge_memberships').fetchone()[0], 99)


if __name__ == '__main__':
    unittest.main()
