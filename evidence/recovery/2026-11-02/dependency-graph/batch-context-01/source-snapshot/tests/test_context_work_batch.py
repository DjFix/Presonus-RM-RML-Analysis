"""Canonical-vs-batch work validation parity against isolated real SQLite data."""
import copy
import json
import pathlib
import shutil
import sqlite3
import sys
import unittest
import uuid
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'dependency-graph'))
import dedup_index
import dedup_work
from context_runtime import ContextError, sha
from context_work_batch import BatchWorkValidator


class WorkBatchParityTests(unittest.TestCase):
    def setUp(self):
        self.root = ROOT / 'temp/test-work/context-work-batch' / uuid.uuid4().hex
        (self.root / 'dependency-graph').mkdir(parents=True)
        self.db = self.root / 'work.sqlite'
        native = self.root / 'native.sqlite'
        native.write_bytes(b'isolated native input fixture')
        report = self.root / 'report.json'
        report.write_text('{}')
        self.release = self.root / 'release.json'
        self.release.write_text('{}')
        pointer = {'database': 'native.sqlite', 'sha256': sha(native),
                   'report': 'report.json', 'report_sha256': sha(report)}
        (self.root / 'dependency-graph/NATIVE_ACTIVE.json').write_text(json.dumps(pointer))
        (self.root / 'dependency-graph/DEDUP_ACTIVE.json').write_text(json.dumps({
            'database': 'work.sqlite', 'generation': 'generation', 'schema_version': 1}))
        with sqlite3.connect(self.db) as connection:
            connection.executescript((ROOT / 'dependency-graph/dedup_schema.sql').read_text())
            metadata = {'complete': True, 'generation': 'generation', 'native_generation': sha(native),
                        'release_inputs': {'release.json': sha(self.release)},
                        'producer_inputs': {p: sha(ROOT / 'dependency-graph' / p)
                            for p in ['dedup_index.py', 'dedup_work.py', 'dedup_schema.sql']}}
            connection.executemany('INSERT INTO index_meta VALUES(?,?)',
                                   [(key, json.dumps(value)) for key, value in metadata.items()])
            connection.execute('INSERT INTO equivalence_decisions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                ('decision', 'subject', 1, 'test', 'verified', 'bounded fixture', 'test reason',
                 '[]', '[]', 'fixture', 'a' * 64, 'fixture', 'generation', '2026-11-02'))
            connection.execute('INSERT INTO reconstruction_work_items(id,work_kind,subject_id,decision_id) VALUES(?,?,?,?)',
                               ('work', 'reconstruct', 'subject', 'decision'))
            connection.execute('INSERT INTO work_claims VALUES(?,?,?,?,?,?,?,?)',
                               ('claim', 'work', 'owner', 'packet', 'active', 'generation', 'decision', 'now'))
        self.packet = {'originals': [{'original': {'anchor': 'anchor'}}], 'work_binding': {
            'database': 'work.sqlite', 'generation': 'generation', 'claim_id': 'claim',
            'claim_owner': 'owner', 'work_item_id': 'work', 'equivalence_decision_id': 'decision',
            'decision_revision': 1, 'unique_payload_dependencies': [],
            'covered_occurrences': [{'catalog_anchor': 'anchor'}]}}
        original_verify = dedup_index.verify_inputs
        patch = mock.patch.object(dedup_work, 'verify_inputs',
                                  side_effect=lambda connection, root=None: original_verify(connection, root or self.root))
        patch.start()
        self.addCleanup(patch.stop)
        canonical_evidence = dedup_work.evidence
        evidence_patch = mock.patch.object(dedup_work,'evidence',lambda refs:canonical_evidence(refs,self.root))
        evidence_patch.start()
        self.addCleanup(evidence_patch.stop)

    def execute(self, sql, args=()):
        with sqlite3.connect(self.db) as connection:
            connection.execute(sql, args)

    def assert_both_reject(self, packet=None):
        packet = self.packet if packet is None else packet
        for mode in ['canonical', 'batch']:
            with self.subTest(mode=mode):
                with self.assertRaises((ContextError, OSError)):
                    if mode == 'canonical':
                        dedup_work.validate_packet_work(self.root, packet, 'packet')
                    else:
                        validator = BatchWorkValidator(self.root)
                        try:
                            validator.validate(packet, 'packet')
                            validator.finish()
                        finally:
                            validator.close()

    def test_identical_valid_binding_passes_canonical_and_batch(self):
        dedup_work.validate_packet_work(self.root, self.packet, 'packet')
        validator = BatchWorkValidator(self.root)
        try:
            validator.validate(self.packet, 'packet')
            validator.finish()
        finally:
            validator.close()

    def test_claim_status_owner_path_work_generation_and_decision_mutations(self):
        for column, value in [('state', 'released'), ('owner', 'other'), ('packet_path', 'foreign'),
                              ('work_item_id', 'absent'), ('generation', 'other'), ('decision_id', 'other')]:
            with self.subTest(column=column):
                with sqlite3.connect(self.db) as connection:
                    original = connection.execute('SELECT ' + column + ' FROM work_claims').fetchone()[0]
                self.execute('UPDATE work_claims SET ' + column + '=?', (value,))
                self.assert_both_reject()
                self.execute('UPDATE work_claims SET ' + column + '=?', (original,))

    def test_work_completion_and_covered_original_mismatch(self):
        self.execute('UPDATE reconstruction_work_items SET status="completed"')
        self.assert_both_reject()
        self.execute('UPDATE reconstruction_work_items SET status="todo"')
        changed = copy.deepcopy(self.packet)
        changed['originals'][0]['original']['anchor'] = 'other'
        self.assert_both_reject(changed)

    def test_new_decision_revision_is_detected(self):
        self.execute('INSERT INTO equivalence_decisions SELECT "new",subject_id,2,equivalence_kind,status,verification_scope,reason,members,evidence_refs,producer_identity,producer_sha256,policy_version,input_generation,created_at FROM equivalence_decisions')
        self.assert_both_reject()

    def test_batch_finish_rechecks_live_claims_and_immutable_inputs(self):
        for mutation in ['claim', 'release']:
            with self.subTest(mutation=mutation):
                validator = BatchWorkValidator(self.root)
                original = self.release.read_bytes()
                try:
                    validator.validate(self.packet, 'packet')
                    if mutation == 'claim':
                        self.execute('UPDATE work_claims SET owner="other"')
                    else:
                        self.release.write_text('changed immutable input')
                    with self.assertRaises(ContextError):
                        validator.finish()
                finally:
                    validator.close()
                    self.execute('UPDATE work_claims SET owner=?', ('owner',))
                    self.release.write_bytes(original)

    def test_missing_binding_and_empty_coverage_parity(self):
        self.assert_both_reject({})
        changed = copy.deepcopy(self.packet)
        changed['originals'] = []
        self.assert_both_reject(changed)

    def test_superseded_work_parity(self):
        self.execute('UPDATE reconstruction_work_items SET status="superseded"')
        self.assert_both_reject()

    def test_payload_and_decision_evidence_parity(self):
        payload = self.root/'payload.bin'
        payload.write_bytes(b'payload')
        packet = copy.deepcopy(self.packet)
        packet['work_binding']['unique_payload_dependencies'] = [
            {'object_path':'payload.bin','size':7,'content_sha256':sha(payload)}]
        dedup_work.validate_packet_work(self.root,packet,'packet')
        validator = BatchWorkValidator(self.root)
        try:
            validator.validate(packet,'packet')
            payload.write_bytes(b'corrupt')
            self.assert_both_reject(packet)
            with self.assertRaises(ContextError): validator.finish()
        finally: validator.close()
        refs = json.dumps([{'path':'payload.bin','sha256':'0'*64}])
        self.execute('INSERT INTO equivalence_decisions SELECT \"evidence-decision\",\"evidence-subject\",1,equivalence_kind,status,verification_scope,reason,members,?,producer_identity,producer_sha256,policy_version,input_generation,created_at FROM equivalence_decisions',(refs,))
        self.execute('UPDATE work_claims SET decision_id=?',('evidence-decision',))
        self.packet['work_binding']['equivalence_decision_id'] = 'evidence-decision'
        self.assert_both_reject()

    def test_exact_immutable_keys_change_rejects_reuse(self):
        for key in ('release_inputs','producer_inputs','native_generation','generation','complete'):
            with self.subTest(key=key):
                validator = BatchWorkValidator(self.root)
                try:
                    with sqlite3.connect(self.db) as connection:
                        previous = connection.execute('SELECT value FROM index_meta WHERE key=?',(key,)).fetchone()[0]
                    self.execute('UPDATE index_meta SET value=? WHERE key=?',(json.dumps('changed'),key))
                    with self.assertRaises(ContextError): validator.validate(self.packet,'packet')
                finally:
                    validator.close()
                    self.execute('UPDATE index_meta SET value=? WHERE key=?',(previous,key))

    def test_late_native_change_fails_final_barrier(self):
        validator = BatchWorkValidator(self.root)
        try:
            validator.validate(self.packet,'packet')
            (self.root/'native.sqlite').write_bytes(b'changed')
            with self.assertRaises(ContextError): validator.finish()
        finally: validator.close()

    def test_native_pointer_change_rejects_reuse(self):
        validator = BatchWorkValidator(self.root)
        try:
            path = self.root/'dependency-graph/NATIVE_ACTIVE.json'
            pointer = json.loads(path.read_text())
            pointer['report_sha256'] = '0'*64
            path.write_text(json.dumps(pointer))
            with self.assertRaises(ContextError): validator.validate(self.packet,'packet')
        finally: validator.close()

    def test_database_replacement_rejects_stale_connection(self):
        validator = BatchWorkValidator(self.root)
        try:
            replacement = self.root/'replacement.sqlite'
            shutil.copyfile(self.db,replacement)
            replacement.replace(self.db)
            with self.assertRaisesRegex(ContextError,'replaced'): validator.validate(self.packet,'packet')
        finally: validator.close()


if __name__ == '__main__':
    unittest.main()
