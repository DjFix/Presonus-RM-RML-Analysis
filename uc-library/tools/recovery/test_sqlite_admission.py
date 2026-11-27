import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import catalog
import sqlite_admission as admission
import sqlite_packet as packet
from test_sqlite_packet import fixture


class CompletionTest(unittest.TestCase):
    def test_scoped_completion_idempotence_and_proof_drift(self):
        workspace = packet.ROOT / 'temp/recovery-work'
        with TemporaryDirectory(prefix='sqlite-admission-test-', dir=workspace) as scratch:
            root, db, plan = fixture(Path(scratch))
            packet_dir = root / 'temp/recovery-work/packet'
            index = packet.prepare(root, plan, packet_dir, db)
            packet.dispatch(root, packet_dir, db)
            targets = [packet.load(packet_dir/'tasks'/task/'CONTEXT.json')['originals'][0]['original']
                       for task in sorted(index['tasks'])]
            proof = root/'uc-library/current-proof.json'
            packet.write(proof, {'passed': True})
            rows = [
                {'original_elf_sha256': row['elf'], 'mangled': row['mangled'],
                 'portable_ready': True, 'domain': 'Synthetic journal fixture.',
                 'validation': proof.name, 'validation_sha256': packet.digest(proof)}
                for row in targets
            ]
            pending = dict(rows[1], portable_ready=False, cpp_compiled=True,
                           mangling_namespace_checked=True, declaration_uncertainties=['fixture return'],
                           behavior_validation=proof.name, behavior_validation_sha256=packet.digest(proof))
            with packet.adapter.snapshot(root/'uc-library', db=db) as prior:
                guard = prior.guard
            commit = packet.adapter.commit_snapshot(rows[:1], [pending], guard, library=root/'uc-library',
                db=db, actor='fixture', reason='Synthetic guarded admission')
            result = root/'guarded-receipt.json'
            packet.write(result, {'sqlite_commit': commit})
            first = sorted(index['tasks'])[0]
            dry = admission.finalize(root, packet_dir, result, db, [first])
            self.assertTrue(dry['catalog']['dry_run'])
            self.assertEqual(dry['catalog']['operations'], 1)
            self.assertEqual([r['state'] for r in catalog.query(db)], ['assigned', 'assigned'])
            admission.finalize(root, packet_dir, result, db, [first], apply=True)
            replay = admission.finalize(root, packet_dir, result, db, [first], apply=True)
            self.assertTrue(replay['catalog']['idempotent_replay'])
            self.assertEqual(sorted(r['state'] for r in catalog.query(db)), ['assigned', 'done'])
            second = sorted(index['tasks'])[1]
            self.assertEqual(admission.finalize(root, packet_dir, result, db, [second])
                             ['readback'][0]['classification'], 'pending')
            proof.write_text('proof drift')
            with self.assertRaisesRegex(ValueError, 'Admitted proof changed'):
                admission.finalize(root, packet_dir, result, db, list(index['tasks']), apply=True)
            self.assertEqual(sorted(r['state'] for r in catalog.query(db)), ['assigned', 'done'])


ROOT = packet.ROOT

class ChainTest(unittest.TestCase):
    def setUp(self):
        self.scratch=TemporaryDirectory(prefix='admission-chain-',dir=ROOT/'temp/recovery-work')
        self.addCleanup(self.scratch.cleanup)
        self.root,self.db,plan=fixture(Path(self.scratch.name))
        self.packet=self.root/'temp/recovery-work/packet';self.index=packet.prepare(self.root,plan,self.packet,self.db);packet.dispatch(self.root,self.packet,self.db)
        self.task=sorted(self.index['tasks'])[0]
        data=packet.load(self.packet/'tasks'/self.task/'CONTEXT.json');target=data['originals'][0]['original'];self.anchor=target['anchor']
        proof=self.root/'uc-library/current-proof.json';packet.write(proof,{'passed':True})
        row={'original_elf_sha256':target['elf'],'mangled':target['mangled'],'portable_ready':True,'domain':'Exact synthetic admitted identity for chain integrity test.','validation':proof.name,'validation_sha256':packet.digest(proof)}
        with packet.adapter.snapshot(self.root/'uc-library',db=self.db) as prior:guard=prior.guard
        commit=packet.adapter.commit_snapshot([row],[],guard,library=self.root/'uc-library',db=self.db,actor='fixture',reason='Guarded test admission')
        self.receipt=self.root/'guarded-receipt.json';packet.write(self.receipt,{'sqlite_commit':commit});self.seq=0
    def live(self):
        with packet.connection(self.db) as db:return dict(db.execute('SELECT * FROM catalog_tasks WHERE anchor=?',(self.anchor,)).fetchone())
    def update(self,**fields):
        old=self.live();self.seq+=1
        catalog.operate(self.db,{'request_id':'chain-test-'+str(self.seq),'actor':'fixture','operations':[dict(anchor=self.anchor,expected_revision=old['revision'],reason='Exact isolated chain transition',**fields)]},dry_run=False)
    def final(self,**kw):return admission.finalize(self.root,self.packet,self.receipt,self.db,[self.task],allow_same_owner_chain=True,**kw)
    def test_reserialized_additive_notes_preserved_and_idempotent(self):
        old=self.live();note=json.loads(old['notes']);note['reconstruction_remarks']=[{'reason':'parked exact source','retained':True}]
        latest=json.dumps(note,indent=2);self.update(notes=latest)
        dry=self.final();self.assertTrue(dry['catalog']['dry_run']);self.assertEqual(self.live()['notes'],latest)
        self.final(apply=True);live=self.live();self.assertEqual(live['state'],'done');self.assertTrue(live['notes'].startswith(latest+'\n'))
        self.assertTrue(self.final(apply=True)['catalog']['idempotent_replay'])
    def test_default_strict_rejects_advanced_revision(self):
        self.update(notes=self.live()['notes']+'\nRetained append.')
        with self.assertRaisesRegex(ValueError,'Stale task revision'):admission.finalize(self.root,self.packet,self.receipt,self.db,[self.task],apply=True)
        self.assertEqual(self.live()['state'],'assigned')
    def test_changed_semantic_value_rejected(self):
        note=json.loads(self.live()['notes']);note['packet_sha256']='0'*64;self.update(notes=json.dumps(note))
        with self.assertRaisesRegex(ValueError,'notes changed'):self.final()
    def test_owner_change_and_restoration_rejected(self):
        owner=self.live()['owner'];self.update(owner=owner+'_changed');self.update(owner=owner)
        with self.assertRaisesRegex(ValueError,'owner or batch'):self.final()
    def test_state_change_and_restoration_rejected(self):
        self.update(state='blocked',notes=self.live()['notes']+'\nBlocked fixture.');self.update(state='assigned')
        with self.assertRaisesRegex(ValueError,'uninterrupted'):self.final()
    def test_batch_change_rejected(self):
        self.update(batch='different_batch')
        with self.assertRaisesRegex(ValueError,'owner or batch'):self.final()
    def test_list_reorder_and_removal_rejected(self):
        note=json.loads(self.live()['notes']);note['owned_files']=list(reversed(note['owned_files']));self.update(notes=json.dumps(note))
        with self.assertRaisesRegex(ValueError,'notes changed'):self.final()
    def test_transactional_guard_detects_concurrent_note_change(self):
        self.update(notes=self.live()['notes']+'\nFirst safe append.')
        original=admission.catalog.operate
        def race(db,payload,**kw):
            row=self.live();self.update(notes=row['notes']+'\nConcurrent append.')
            return original(db,payload,**kw)
        # Change only this invocation; update uses the original operator.
        def wrapped(db,payload,**kw):
            admission.catalog.operate=original
            try:return race(db,payload,**kw)
            finally:admission.catalog.operate=wrapped
        admission.catalog.operate=wrapped
        try:
            with self.assertRaisesRegex(ValueError,'assignment changed'):self.final(apply=True)
        finally:admission.catalog.operate=original
        self.assertEqual(self.live()['state'],'assigned')
    def test_broken_journal_link_rejected_without_database_mutation(self):
        self.update(notes=self.live()['notes']+'\nSafe append.')
        with packet.connection(self.db) as db:
            assigned=db.execute('SELECT previous_revision,new_revision,new_state FROM catalog_journal WHERE anchor=? ORDER BY sequence LIMIT 1',(self.anchor,)).fetchone()
            entries=[dict(x) for x in db.execute('SELECT request_id,previous_revision,new_revision,previous_state,new_state FROM catalog_journal WHERE anchor=? AND new_revision>? ORDER BY sequence',(self.anchor,assigned['new_revision']))]
            entries[0]['previous_revision']+=1
            class ReadOnlyBrokenJournal:
                def execute(inner,query,args):
                    if 'FROM catalog_journal' in query:
                        class Rows:
                            def fetchall(inner):return entries
                        return Rows()
                    return db.execute(query,args)
            state=json.loads(assigned['new_state'])
            with self.assertRaisesRegex(ValueError,'Broken assignment'):
                admission.assignment_chain(ReadOnlyBrokenJournal(),self.anchor,assigned,state['owner'],state['batch'],'not-completion')

    def test_note_parser_does_not_allow_non_json_rewrite(self):
        self.assertFalse(admission.additive_notes('plain initial','replacement plain'))
        self.assertFalse(admission.additive_notes('{"a":1,"b":2}','{"b":2,"a":1,"c":3}'))
        self.assertFalse(admission.additive_notes('{"a":[1,2]}','{"a":[2,1]}'))
        self.assertFalse(admission.additive_notes('{"a":[1]}','{"a":[true]}'))
        self.assertTrue(admission.additive_notes('{"a":[1]}','{ "a": [1,2], "new": true }'))
