"""Prove exact owner reconciliation against the existing remove/replace path."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from compact_facts import create_schema
from context_runtime import sha
from incremental_stage import IncrementalStage
from owner_rekey_plan import pair_removed_owners
from publication_budget import BudgetExceeded, BudgetLimits, PublicationBudget
from test_bounded_net_changes import node, rows


class OwnerRekeyTests(unittest.TestCase):
    def setUp(self):
        scratch = Path.cwd() / 'temp' / 'test-work'
        scratch.mkdir(parents=True, exist_ok=True)
        self.directory = Path(self.enterContext(tempfile.TemporaryDirectory(dir=scratch)))
        self.old = 'compile:z-retired'
        self.peer = 'compile:m-peer'
        self.new = 'compile:a-current'
        self.command = dict(file='app.cpp', directory=str(self.directory), output='app.o')
        self.peer_command = dict(self.command, file='peer.cpp', output='peer.o')
        self.old_obs = tuple(self.directory / f'old-{suffix}.json' for suffix in ('ast', 'gcc'))
        self.new_obs = tuple(self.directory / f'new-{suffix}.json' for suffix in ('ast', 'gcc'))
        for path in self.old_obs + self.new_obs:
            path.write_text(json.dumps({'fixture': path.stem}))
        self.shared = ('shared', 'shared', 'CALLS', '{"line":7}')
        self.retired = ('shared', 'previous', 'CALLS', '{"line":9}')
        self.incoming = ('shared', 'current', 'CALLS', '{"line":9}')
        self.owner_node = node('retired owner', val='retired', source_definition=True, compiler_definition=False)

    def open_fixture(self, relative):
        path = self.directory / relative
        db = self.enterContext(closing(sqlite3.connect(path)))
        db.execute('PRAGMA journal_mode=WAL')
        create_schema(db)
        db.execute('CREATE TABLE IF NOT EXISTS unit_observations(owner TEXT PRIMARY KEY, observation_id TEXT, payload TEXT)')
        db.execute('CREATE VIEW IF NOT EXISTS units AS SELECT owner,payload FROM unit_observations')
        db.commit()
        with db:
            db.execute('BEGIN')
            stage = IncrementalStage(db, self.budget())
            stage.replace_unit(self.old, self.command, {'shared': self.owner_node, 'previous': node('retired')},
                               [self.shared, self.retired], {'app.cpp': 'old-input'}, *self.old_obs)
            stage.replace_unit(self.peer, self.peer_command,
                               {'shared': node('peer winner', val='peer', source_definition=False,
                                               compiler_definition=True)},
                               [self.shared], {'peer.cpp': 'stable'}, *self.old_obs)
        return db

    @staticmethod
    def budget(**limits):
        return PublicationBudget(BudgetLimits(**limits), io_reader=lambda: 0)

    @staticmethod
    def readback(db):
        return {name: sorted(db.execute('SELECT * FROM ' + name), key=repr)
                for name in ('node_facts', 'edge_facts', 'unit_observations')}

    def replace_current(self, stage):
        stage.replace_unit(self.new, self.command, {'shared': self.owner_node, 'current': node('current')},
                           [self.shared, self.incoming], {'app.cpp': 'new-input'}, *self.new_obs,
                           {'system.hpp': 'current-system-input'})

    def test_pair_requires_unique_same_group_source_and_output(self):
        db = self.open_fixture('pairs.sqlite')
        pair = lambda selected: pair_removed_owners(db, [self.old], selected)
        self.assertEqual(pair([(self.new, self.command)]), {self.new: self.old})
        for invalid in (
            [(self.new, self.command), ('compile:duplicate', self.command)],
            [(self.new, dict(self.command, file='other.cpp'))],
            [(self.new, dict(self.command, output='other.o'))],
            [('other:a-current', self.command)],
        ):
            with self.subTest(selected=invalid):
                self.assertEqual(pair(invalid), {})

    def test_rekey_matches_legacy_and_preserves_fresh_capture_provenance(self):
        outcomes = {}
        for bounded in (False, True):
            db = self.open_fixture(f'facts-{bounded}.sqlite')
            delta = self.enterContext(closing(sqlite3.connect(self.directory / f'delta-{bounded}.sqlite')))
            old_id, = db.execute('SELECT owner_id FROM compact_owners WHERE value=?', (self.old,)).fetchone()
            old_observation, = db.execute('SELECT observation_id FROM unit_observations WHERE owner=?',
                                          (self.old,)).fetchone()
            db.execute('BEGIN IMMEDIATE')
            delta.execute('BEGIN')
            stage = IncrementalStage(db, self.budget(), bounded=bounded)
            try:
                if bounded:
                    self.assertEqual(stage.rekey_owner(self.old, self.new), old_observation)
                    self.assertEqual(db.execute('SELECT owner_id FROM compact_owners WHERE value=?',
                                                (self.new,)).fetchone(), (old_id,))
                else:
                    stage.remove_owner(self.old)
                self.replace_current(stage)
                counts = stage.finish(delta)
            finally:
                stage.close()
            db.commit()
            delta.commit()
            exact_events = {name: sorted(row[1:] for row in values) for name, values in rows(delta).items()}
            outcomes[bounded] = (self.readback(db), counts, exact_events)
            current_id, payload = db.execute('SELECT observation_id,payload FROM unit_observations WHERE owner=?',
                                             (self.new,)).fetchone()
            self.assertNotEqual(current_id, old_observation)
            self.assertIsNone(db.execute('SELECT 1 FROM unit_observations WHERE owner=?', (self.old,)).fetchone())
            payload = json.loads(payload)
            self.assertEqual(payload['inputs'], {'app.cpp': 'new-input'})
            self.assertEqual(payload['external_inputs'], {'system.hpp': 'current-system-input'})
            for key, path in zip(('ast', 'gcc'), self.new_obs, strict=True):
                self.assertEqual(payload[key + '_sha256'], sha(path))
        self.assertEqual(outcomes[True], outcomes[False])
        events = outcomes[True][2]
        self.assertEqual(events['old_edges'], [self.retired])
        self.assertEqual(events['new_edges'], [self.incoming])
        winner = next(row for row in events['nodes'] if row[0] == 'shared')
        self.assertEqual(winner[2], 'peer winner')
        self.assertEqual(json.loads(winner[3]), dict(val='peer', source_definition=True, compiler_definition=True))

    def test_later_budget_failure_rolls_back_rekey_and_old_observation(self):
        db = self.open_fixture('rollback.sqlite')
        original = self.readback(db)
        db.execute('BEGIN IMMEDIATE')
        stage = IncrementalStage(db, self.budget(rows=3), bounded=True)
        try:
            stage.rekey_owner(self.old, self.new)
            self.assertEqual(db.execute('SELECT count(*) FROM units WHERE owner=?', (self.old,)).fetchone(), (0,))
            with self.assertRaises(BudgetExceeded):
                self.replace_current(stage)
        finally:
            stage.close()
            db.rollback()
        self.assertEqual(self.readback(db), original)


if __name__ == '__main__':
    unittest.main()
