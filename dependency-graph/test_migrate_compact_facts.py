"""One-time migration tests use handcrafted local legacy stores only."""
import hashlib
import json
import pathlib
import sqlite3
import unittest
import uuid
from unittest.mock import patch

import migrate_compact_facts
from migrate_compact_facts import MigrationError, migrate

ROOT = pathlib.Path(__file__).resolve().parents[1]


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.out = ROOT / 'temp/test-work/compact-migration' / uuid.uuid4().hex
        self.out.mkdir(parents=True)
        self.source = self.out / 'legacy.sqlite'
        self.destination = self.out / 'replacement.sqlite'
        self.report = self.out / 'receipt.json'
        db = sqlite3.connect(self.source)
        db.executescript('''
          CREATE TABLE node_facts(owner,id,kind,label,metadata,PRIMARY KEY(owner,id));
          CREATE TABLE edge_facts(owner,src,dst,kind,evidence,PRIMARY KEY(owner,src,dst,kind,evidence));
          CREATE TABLE units(owner PRIMARY KEY,payload);
          CREATE TABLE observations(id PRIMARY KEY,owner,payload);
          CREATE TABLE current_observations(owner PRIMARY KEY,observation_id);
          CREATE TABLE meta(key PRIMARY KEY,value);
        ''')
        db.executemany('INSERT INTO meta VALUES(?,?)', [('identity_version', '2'),
            ('unregistered_baseline', 'prior-proof'), ('catalog_snapshot', 'snapshot-hash')])
        # Shared values, special owners, edge-only owners and units with no facts.
        nodes = [('a', 'fn', 'Function', 'fn', '{"b": 2, "a": 1}'),
                 ('b', 'fn', 'Function', 'fn', '{"a":1,"b":2}'),
                 ('@catalog', 'catalog:native', 'Function', 'native', '{"elf_sha256":"firmware-hash"}'),
                 ('@build', 'build:root', 'Build', 'root', '{}')]
        db.executemany('INSERT INTO node_facts VALUES(?,?,?,?,?)', nodes)
        db.executemany('INSERT INTO edge_facts VALUES(?,?,?,?,?)',
                       [(owner, 'fn', 'catalog:native', 'CALLS', '{"line": 1,"path":"unit.cpp"}')
                        for owner in ('a', 'b', 'edges-only')])
        for owner in ('a', 'unit-only'):
            payload = {'command': {'file': owner + '.cpp'}, 'inputs': {'header.hpp': 'hash'},
                       'ast': 'capture/ast.json', 'gcc': 'capture/gcc.json',
                       'ast_sha256': 'ast-hash', 'gcc_sha256': 'gcc-hash'}
            db.execute('INSERT INTO units VALUES(?,?)', (owner, json.dumps(payload)))
            db.execute('INSERT INTO current_observations VALUES(?,?)', (owner, 'current-' + owner))
            db.execute('INSERT INTO observations VALUES(?,?,?)',
                       ('current-' + owner, owner, json.dumps(dict(payload, owner=owner, identity_version=2))))
        db.execute('INSERT INTO observations VALUES(?,?,?)', ('historical-unused', 'a', '{"old":"history"}'))
        db.commit()
        db.close()

    def source_hash(self):
        return hashlib.sha256(self.source.read_bytes()).hexdigest()

    def test_exact_current_fact_equivalence_and_history_not_copied(self):
        before = self.source_hash()
        receipt = migrate(self.source, self.destination, self.report)
        self.assertEqual(receipt['status'], 'verified')
        self.assertEqual(receipt['counts'], {'owners': 6, 'nodes': 4, 'edges': 3, 'units': 2})
        self.assertEqual(receipt['destination_observations'], 2)
        self.assertFalse(receipt['history_copied'])
        self.assertEqual(receipt, json.loads(self.report.read_text()))
        self.assertGreater(receipt['elapsed_seconds'], 0)
        self.assertGreater(receipt['destination_bytes'], 0)
        self.assertIn('read_bytes', receipt['process_io_delta'])
        self.assertEqual(self.source_hash(), before)
        with sqlite3.connect(self.source) as old, sqlite3.connect(self.destination) as new:
            for table in ('node_facts', 'edge_facts'):
                original = old.execute('SELECT * FROM ' + table + ' ORDER BY 1,2').fetchall()
                result = new.execute('SELECT * FROM ' + table + ' ORDER BY 1,2').fetchall()
                if table == 'node_facts':
                    original = [(*row[:4], json.loads(row[4])) for row in original]
                    result = [(*row[:4], json.loads(row[4])) for row in result]
                self.assertEqual(original, result)
            for table in ('units', 'current_observations', 'meta'):
                self.assertEqual(old.execute('SELECT * FROM ' + table + ' ORDER BY 1').fetchall(),
                                 new.execute('SELECT * FROM ' + table + ' ORDER BY 1').fetchall())
            self.assertEqual(new.execute("SELECT count(*) FROM observations WHERE id='historical-unused'").fetchone()[0], 0)
            self.assertEqual(new.execute('SELECT count(*) FROM compact_node_values').fetchone()[0], 3)
            self.assertEqual(new.execute('SELECT count(*) FROM compact_logical_edges').fetchone()[0], 1)
            self.assertEqual(new.execute('SELECT count(*) FROM compact_provenance').fetchone()[0], 1)
            self.assertEqual(new.execute('PRAGMA quick_check').fetchall(), [('ok',)])
            self.assertEqual(new.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_migration_import_never_builds_support_or_uses_replace(self):
        with patch.object(migrate_compact_facts.CompactFacts, '_node_support', side_effect=AssertionError('node support')), \
                patch.object(migrate_compact_facts.CompactFacts, '_edge_support', side_effect=AssertionError('edge support')), \
                patch.object(migrate_compact_facts.CompactFacts, 'replace_owner', side_effect=AssertionError('replace')):
            receipt = migrate(self.source, self.destination, self.report)
        self.assertEqual(receipt['status'], 'verified')

    def test_pending_rejected_before_replacement_creation(self):
        with sqlite3.connect(self.source) as db:
            db.execute("INSERT INTO meta VALUES('pending','live-journal')")
        before = self.source_hash()
        with self.assertRaisesRegex(MigrationError, 'Pending publication'):
            migrate(self.source, self.destination, self.report)
        self.assertFalse(self.destination.exists())
        self.assertFalse(self.report.exists())
        self.assertEqual(self.source_hash(), before)

    def test_existing_outputs_refused_without_retry_or_overwrite(self):
        self.destination.write_bytes(b'existing replacement')
        with self.assertRaises(FileExistsError):
            migrate(self.source, self.destination, self.report)
        self.assertEqual(self.destination.read_bytes(), b'existing replacement')
        self.assertEqual(list(self.out.glob('replacement*')), [self.destination])
        self.assertFalse(self.report.exists())

    def test_live_wal_writer_rejected_without_source_changes(self):
        writer = sqlite3.connect(self.source)
        self.addCleanup(writer.close)
        writer.execute('PRAGMA journal_mode=WAL')
        writer.execute("UPDATE meta SET value='uncommitted' WHERE key='identity_version'")
        with self.assertRaisesRegex(MigrationError, 'active writer'):
            migrate(self.source, self.destination, self.report)
        self.assertFalse(self.destination.exists())
        writer.rollback()
        self.assertEqual(writer.execute("SELECT value FROM meta WHERE key='identity_version'").fetchone()[0], '2')

    def test_committed_wal_rows_are_included_in_read_snapshot(self):
        keeper = sqlite3.connect(self.source)
        self.addCleanup(keeper.close)
        keeper.execute('PRAGMA journal_mode=WAL')
        keeper.execute("INSERT INTO node_facts VALUES('wal-owner','wal-node','Data','wal','{}')")
        keeper.commit()
        wal = pathlib.Path(str(self.source) + '-wal')
        self.assertTrue(wal.exists())
        before = hashlib.sha256(wal.read_bytes()).hexdigest()
        receipt = migrate(self.source, self.destination, self.report)
        with sqlite3.connect(self.destination) as migrated:
            self.assertEqual(migrated.execute("SELECT label FROM node_facts WHERE id='wal-node'").fetchone(), ('wal',))
        self.assertGreater(receipt['source_wal_bytes'], 0)
        self.assertEqual(hashlib.sha256(wal.read_bytes()).hexdigest(), before)

    def test_source_writer_lock_is_held_during_independent_verification(self):
        original = migrate_compact_facts._verify_owner
        calls = []
        def verify(source, destination, owner):
            writer = sqlite3.connect(self.source, timeout=0)
            try:
                with self.assertRaisesRegex(sqlite3.OperationalError, 'locked'):
                    writer.execute('BEGIN IMMEDIATE')
            finally:
                writer.close()
            calls.append(owner)
            return original(source, destination, owner)
        with patch.object(migrate_compact_facts, '_verify_owner', side_effect=verify):
            migrate(self.source, self.destination, self.report)
        self.assertEqual(len(calls), 6)

    def test_nonempty_source_rollback_journal_is_not_recovered_or_modified(self):
        journal = pathlib.Path(str(self.source) + '-journal')
        journal.write_bytes(b'operator must resolve this journal')
        before = self.source_hash()
        with self.assertRaisesRegex(MigrationError, 'rollback journal'):
            migrate(self.source, self.destination, self.report)
        self.assertEqual(journal.read_bytes(), b'operator must resolve this journal')
        self.assertEqual(self.source_hash(), before)
        self.assertFalse(self.destination.exists())

    def test_source_binding_change_fails_and_retains_single_failed_output(self):
        original = migrate_compact_facts._binding
        calls = []
        def changed(path):
            result = original(path)
            calls.append(path)
            if len(calls) >= 3:
                result['main']['mtime_ns'] += 1
            return result
        with patch.object(migrate_compact_facts, '_binding', side_effect=changed):
            with self.assertRaisesRegex(MigrationError, 'binding/data_version changed'):
                migrate(self.source, self.destination, self.report)
        self.assertTrue(self.destination.exists())
        self.assertEqual(json.loads(self.report.read_text())['status'], 'failed')
        with self.assertRaises(FileExistsError):
            migrate(self.source, self.destination, self.report)

    def test_current_observation_must_bind_unit_and_owner(self):
        with sqlite3.connect(self.source) as db:
            db.execute("UPDATE observations SET payload='{}' WHERE id='current-a'")
        with self.assertRaisesRegex(MigrationError, 'does not bind current unit'):
            migrate(self.source, self.destination, self.report)
        self.assertEqual(json.loads(self.report.read_text())['status'], 'failed')

    def test_independent_verification_detects_corrupted_migrated_fact(self):
        original = migrate_compact_facts.CompactFacts.import_owner
        def corrupt(store, owner, nodes, edges):
            result = original(store, owner, nodes, edges)
            if owner == 'a':
                store.db.execute("UPDATE compact_node_values SET label='corruption' WHERE label='fn'")
            return result
        with patch.object(migrate_compact_facts.CompactFacts, 'import_owner', new=corrupt):
            with self.assertRaisesRegex(MigrationError, 'Owner facts differ'):
                migrate(self.source, self.destination, self.report)
        self.assertEqual(json.loads(self.report.read_text())['status'], 'failed')


if __name__ == '__main__':
    unittest.main()
