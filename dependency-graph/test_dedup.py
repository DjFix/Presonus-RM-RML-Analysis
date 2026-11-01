"""Safety boundaries for equivalence and transactional unique work."""
import concurrent.futures
import json
import pathlib
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import dedup_index as d
import dedup_work as w
from context_runtime import ContextError
from native_graph import key

ROOT=pathlib.Path(__file__).resolve().parents[1]
SCRATCH=ROOT/'temp/test-work/dedup'
SCRATCH.mkdir(parents=True,exist_ok=True)


class DedupTests(unittest.TestCase):
    def setUp(self):
        # Retain failed fixtures and claim histories for inspection.
        self.folder=pathlib.Path(tempfile.mkdtemp(dir=SCRATCH))
        self.db=self.folder/'test.sqlite'
        self.c=sqlite3.connect(self.db);self.c.row_factory=sqlite3.Row
        self.c.executescript(pathlib.Path(d.__file__).with_name('dedup_schema.sql').read_text())
        for k,v in [('generation','g1'),('native_generation','n1'),('complete',True)]:
            self.c.execute('INSERT INTO index_meta VALUES(?,?)',(k,d.dump(v)))
        self.c.execute('INSERT INTO external_providers VALUES(?,?)',('ccl','{}'))
        self.originals=[]
        for i in range(2):
            elf=str(i)*64
            self.c.execute('INSERT INTO binary_artifacts(elf_sha256) VALUES(?)',(elf,))
            o={'elf':elf,'mangled':'_Z3foov','address':4096,'size':4,'section_json':'1','anchor':'a'+str(i)}
            self.originals.append({'original':o,'record':None})
            self.c.execute('INSERT INTO symbol_occurrences(id,native_id,catalog_anchor,elf_sha256,original_mangled,symbol_kind,strategy,binding_status,provider_binding) VALUES(?,?,?,?,?,?,?,?,?)',('o'+str(i),w.target_key(o),o['anchor'],elf,o['mangled'],'STT_FUNC','reconstruct','unmatched','{}'))
            self.c.execute('INSERT INTO dependency_observations VALUES(?,?,?,?)',('o'+str(i),'complete','[]','[]'))
        self.c.commit()
        self.patcher=patch.object(w,'verify_inputs',lambda *args:None);self.patcher.start()

    def tearDown(self):
        self.patcher.stop();self.c.close()

    def task(self,mode='research'):
        return {'task_id':'worker','mode':mode,'originals':self.originals,'targets':[]}

    def shared(self):
        did=d.decision(self.c,'shared','implementation','verified','shared_portable_implementation','fixture',['o0','o1'])
        self.c.execute('INSERT INTO implementation_groups VALUES(?,?,?)',('shared',did,'o0'))
        self.c.executemany('INSERT INTO implementation_members VALUES(?,?)',[('shared','o0'),('shared','o1')])
        wid=d.add_work(self.c,'reconstruct','shared',['o0','o1'],'o0',did)
        self.c.commit();return wid

    def test_same_signature_different_code_contents(self):
        sig=d.digest('itanium','arm-eabi','_Z3foov')
        self.assertEqual(sig,d.digest('itanium','arm-eabi','_Z3foov'))
        self.assertNotEqual(d.digest('arm',32,'little','arm',4,'a'),d.digest('arm',32,'little','arm',4,'b'))

    def test_same_code_different_payloads_rejected(self):
        for i in range(2):self.c.execute('UPDATE dependency_observations SET observations=? WHERE occurrence_id=?',(d.dump([{'payloads':[['payload'+str(i),0]]}]),'o'+str(i)))
        self.assertEqual(d.evaluate(self.c,['o0','o1'])[0],'rejected')

    def test_same_code_resolved_dependencies_one_work(self):
        self.assertEqual(d.evaluate(self.c,['o0','o1'])[0],'verified')
        wid=self.shared();self.assertEqual(w.plan(self.c,self.task())['work_item_id'],wid)
        self.assertEqual(len(w.plan(self.c,self.task())['covered_occurrences']),2)

    def test_alias_interfaces_preserved(self):
        self.c.execute('UPDATE symbol_occurrences SET original_mangled="_Z3barv" WHERE id="o1"')
        self.shared();names={r['original_mangled'] for r in w.plan(self.c,self.task())['covered_occurrences']}
        self.assertEqual(names,{'_Z3foov','_Z3barv'})

    def test_payload_two_occurrences_one_content(self):
        self.c.execute('INSERT INTO payload_contents VALUES(?,?,?,?)',('content',4,'hash','objects/hash'))
        for i in range(2):
            self.c.execute('INSERT INTO binary_ranges(id,elf_sha256,address,size) VALUES(?,?,?,?)',('r'+str(i),str(i)*64,1,4))
            self.c.execute('INSERT INTO payload_occurrences VALUES(?,?,?,?,?)',('p'+str(i),'r'+str(i),'content','symbol size','raw'))
        self.assertEqual(self.c.execute('SELECT count(*) FROM payload_contents').fetchone()[0],1)
        self.assertEqual(self.c.execute('SELECT count(*) FROM payload_occurrences').fetchone()[0],2)

    def test_payload_prefix_different_extent(self):
        self.assertNotEqual(d.digest(3,'abc'),d.digest(4,'abc'))

    def test_compressed_and_expanded_are_separate(self):
        self.assertNotEqual(d.digest(4,'compressed'),d.digest(8,'expanded'))
        self.assertEqual(self.c.execute('SELECT count(*) FROM payload_transformations').fetchone()[0],0)

    def test_nobits_no_fake_content(self):
        self.c.execute('INSERT INTO binary_ranges(id,elf_sha256,size,storage_kind) VALUES(?,?,?,?)',('zero','0'*64,64,'NOBITS'))
        self.assertIsNone(self.c.execute('SELECT content_sha256 FROM binary_ranges WHERE id="zero"').fetchone()[0])

    def test_arm_thumb_different(self):
        self.assertNotEqual(d.digest('arm',32,'little','arm',4,'h'),d.digest('arm',32,'little','thumb',4,'h'))

    def test_incomplete_unknown_blocks(self):
        self.c.execute('UPDATE dependency_observations SET blockers=? WHERE occurrence_id="o0"',(d.dump(['incomplete instruction coverage','unknown range']),))
        self.assertEqual(d.evaluate(self.c,['o0','o1'])[0],'blocked')

    def test_indirect_blocks(self):
        self.c.execute('UPDATE dependency_observations SET blockers=? WHERE occurrence_id="o0"',(d.dump(['indirect dispatch']),))
        self.assertEqual(d.evaluate(self.c,['o0','o1'])[0],'blocked')

    def test_cycle_does_not_self_confirm(self):
        for i in range(2):self.c.execute('UPDATE dependency_observations SET observations=?,blockers=? WHERE occurrence_id=?',(d.dump([{'callee':'o'+str(1-i)}]),d.dump(['unverified callee/component or indirect dispatch']),'o'+str(i)))
        self.assertEqual(d.evaluate(self.c,['o0','o1'])[0],'blocked')

    def test_concurrent_claims_one_owner(self):
        self.shared()
        def acquire(i):
            with d.connect(self.db) as c:return w.claim(c,self.task(),'worker'+str(i),'packet'+str(i))
        with concurrent.futures.ThreadPoolExecutor(2) as pool:results=list(pool.map(acquire,range(2)))
        self.assertEqual(sum(r['acquired'] for r in results),1)
        self.assertEqual(self.c.execute('SELECT count(*) FROM work_claims WHERE state="active"').fetchone()[0],1)

    def test_revision_invalidates_packet(self):
        self.shared();binding=w.claim(self.c,self.task(),'worker','packet')['plan']
        d.decision(self.c,'shared','implementation','blocked','unresolved','new evidence',['o0','o1']);self.c.commit()
        with self.assertRaisesRegex(ContextError,'revision'):w.validate_claim(self.c,binding,'packet')
        binding['generation']='old'
        with self.assertRaisesRegex(ContextError,'generation'):w.validate_claim(self.c,binding,'packet')

    def test_external_routes_binding_only(self):
        for i in range(2):
            self.c.execute('UPDATE symbol_occurrences SET strategy="external_source",provider_id="ccl" WHERE id=?',('o'+str(i),))
            d.add_work(self.c,'provider_binding','o'+str(i),['o'+str(i)],'o'+str(i))
        self.c.commit();task=self.task('reconstruct');task['originals']=task['originals'][:1]
        with self.assertRaisesRegex(ContextError,'external_source'):w.plan(self.c,task)
        task['work_kind']='provider_binding'
        self.assertEqual(w.plan(self.c,task)['work_kind'],'provider_binding')

    def test_repeated_insert_and_decision_idempotent(self):
        self.shared();count=self.c.execute('SELECT count(*) FROM equivalence_decisions').fetchone()[0]
        d.decision(self.c,'shared','implementation','verified','shared_portable_implementation','fixture',['o0','o1'])
        d.add_work(self.c,'reconstruct','shared',['o0','o1'],'o0')
        self.assertEqual(self.c.execute('SELECT count(*) FROM reconstruction_work_items').fetchone()[0],1)
        self.assertEqual(self.c.execute('SELECT count(*) FROM equivalence_decisions').fetchone()[0],count)

    def test_rejected_both_remain(self):
        for i in range(2):d.add_work(self.c,'reconstruct','o'+str(i),['o'+str(i)],'o'+str(i))
        self.c.commit()
        self.assertEqual(self.c.execute('SELECT count(*) FROM reconstruction_work_items').fetchone()[0],2)

    def test_empty_all_modes(self):
        from native_context import require_nonempty
        for mode in ('audit','research','reconstruct'):
            with self.assertRaises(ContextError):require_nonempty({'mode':mode,'originals':self.originals})

    def test_no_timeout_claim_stealing(self):
        self.shared();binding=w.claim(self.c,self.task(),'worker','packet')['plan']
        with self.assertRaisesRegex(ContextError,'process/agent'):
            w.transition(self.c,binding['claim_id'],'release',{'owner':'worker','reason':'timeout'})

    def test_same_work_disjoint_files_conflict(self):
        self.shared();packet={'work_binding':w.claim(self.c,self.task(),'worker','packet')['plan']}
        with patch.object(w,'validate_packet_work'):
            with self.assertRaisesRegex(ContextError,'Duplicate'):w.validate_batch_work(ROOT,[packet,packet],['a','b'])

    def test_review_conflict_preserves_live_claim(self):
        self.shared();binding=w.claim(self.c,self.task(),'worker','packet')['plan']
        proof=self.folder/'proof.json';proof.write_text('{}')
        manifest={'members':['o0','o1'],'status':'rejected','reason':'different domains',
                  'verification_scope':'unresolved','input_generation':'g1',
                  'evidence_refs':[{'path':str(proof.relative_to(ROOT)),'sha256':d.sha(proof)}]}
        result=w.review(self.c,manifest)
        self.assertTrue(result['conflict'])
        self.assertEqual(self.c.execute('SELECT state FROM work_claims WHERE id=?',(binding['claim_id'],)).fetchone()[0],'active')
        self.assertEqual(self.c.execute('SELECT count(*) FROM planning_conflicts').fetchone()[0],1)

    def test_release_requires_live_state_and_keeps_history(self):
        self.shared();binding=w.claim(self.c,self.task(),'worker','packet')['plan']
        w.transition(self.c,binding['claim_id'],'release',{'owner':'worker','reason':'worker never spawned',
                     'live_state_checked':True,'resumable_state_checked':True,'observations':'No DISPATCH and no live process; prepared test only'})
        self.assertEqual(self.c.execute('SELECT count(*) FROM claim_history').fetchone()[0],2)
        second=w.claim(self.c,self.task(),'next','packet2')
        self.assertTrue(second['acquired'])

    def test_result_does_not_cover_group_without_individual_checks(self):
        self.shared();binding=w.claim(self.c,self.task(),'worker','packet')['plan']
        proof=self.folder/'proof.json';proof.write_text('{}')
        with self.assertRaisesRegex(ContextError,'Each original'):
            w.transition(self.c,binding['claim_id'],'complete',{'owner':'worker','reason':'done',
                         'evidence_refs':[{'path':str(proof.relative_to(ROOT)),'sha256':d.sha(proof)}],
                         'common_checks':{'passed':True},'individual_checks':{'o0':{'domain':'test'}}})
        self.assertEqual(self.c.execute('SELECT state FROM work_claims').fetchone()[0],'active')

    def test_reviewed_split_preserves_negative_revision(self):
        self.shared()
        proof=self.folder/'proof.json';proof.write_text('{}')
        result=w.review(self.c,{'members':['o0','o1'],'status':'rejected','reason':'different payloads',
                  'verification_scope':'unresolved','input_generation':'g1',
                  'evidence_refs':[{'path':str(proof.relative_to(ROOT)),'sha256':d.sha(proof)}]})
        self.assertEqual(result['status'],'rejected')
        self.assertEqual(self.c.execute('SELECT count(*) FROM reconstruction_work_items WHERE status="todo"').fetchone()[0],2)
        self.assertEqual(self.c.execute('SELECT count(*) FROM equivalence_decisions').fetchone()[0],2)

    def test_same_elf_two_releases_one_binary(self):
        for version,path in [('1','first/elf'),('2','second/elf')]:
            self.c.execute('INSERT INTO binary_releases VALUES(?,?,?,?,?,?)',(version,'0'*64,version,'client',path,'{}'))
        self.assertEqual(self.c.execute('SELECT count(*) FROM binary_releases').fetchone()[0],2)
        self.assertEqual(self.c.execute('SELECT count(*) FROM binary_artifacts WHERE elf_sha256=?',('0'*64,)).fetchone()[0],1)

    def test_foreign_keys_reject_missing_provenance(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.c.execute('INSERT INTO payload_occurrences VALUES(?,?,?,?,?)',('missing','no-range','no-content','unknown','unknown'))

    def test_packet_payload_full_hash_not_preview(self):
        self.shared();binding=w.claim(self.c,self.task(),'worker','packet')['plan']
        obj=self.folder/'payload';obj.write_bytes(b'a'*256+b'good')
        binding['database']='fixture.sqlite'
        binding['unique_payload_dependencies']=[{'object_path':str(obj.relative_to(ROOT)),'size':260,'content_sha256':d.sha(obj)}]
        packet={'work_binding':binding,'originals':self.originals}
        def opened(root):return d.connect(self.db,True),{'database':'fixture.sqlite'}
        with patch.object(w,'active_index',opened):
            w.validate_packet_work(ROOT,packet,'packet')
            obj.write_bytes(b'a'*256+b'evil')
            with self.assertRaisesRegex(ContextError,'payload object changed'):w.validate_packet_work(ROOT,packet,'packet')

    def test_completed_result_is_excluded(self):
        for i in range(2):
            self.c.execute('INSERT INTO binary_ranges(id,elf_sha256,content_sha256) VALUES(?,?,?)',('r'+str(i),str(i)*64,'h'*64))
            self.c.execute('UPDATE symbol_occurrences SET range_id=? WHERE id=?',('r'+str(i),'o'+str(i)))
        self.shared();binding=w.claim(self.c,self.task(),'worker','packet')['plan']
        proof=self.folder/'proof.json';proof.write_text('{}')
        checks={}
        for item in self.originals:
            o=item['original'];member='o'+o['elf'][0]
            checks[member]={'elf_sha256':o['elf'],'original_mangled':o['mangled'],'range_sha256':'h'*64,
                           'behavioral_domain':'synthetic range intentionally unknown; not original validation',
                           'compiled_mangling_checked':True}
        w.transition(self.c,binding['claim_id'],'complete',{'owner':'worker','reason':'fixture complete',
                     'evidence_refs':[{'path':str(proof.relative_to(ROOT)),'sha256':d.sha(proof)}],
                     'common_checks':{'domain':'synthetic'},'individual_checks':checks})
        with self.assertRaisesRegex(ContextError,'already covered'):w.plan(self.c,self.task())
        self.assertEqual(self.c.execute('SELECT count(*) FROM work_results').fetchone()[0],1)

    def test_review_requires_each_domain_and_fresh_evidence(self):
        self.shared();proof=self.folder/'proof.json';proof.write_text('{}')
        manifest={'members':['o0','o1'],'status':'verified','verification_scope':'shared_portable_implementation',
                  'reason':'same bytes insufficient','input_generation':'g1',
                  'evidence_refs':[{'path':str(proof.relative_to(ROOT)),'sha256':d.sha(proof)}]}
        with self.assertRaisesRegex(ContextError,'dependency/interface'):w.review(self.c,manifest)
        proof.write_text('changed')
        with self.assertRaisesRegex(ContextError,'Evidence changed'):w.review(self.c,manifest)

    def test_dependency_path_aliases_keep_hash_guard(self):
        from refresh_extract import canonical_inputs
        path=str(self.folder/'subdir/../header.hpp')
        canonical=str((self.folder/'header.hpp').resolve())
        self.assertEqual(canonical_inputs({path:'hash',canonical:'hash'}),{canonical:'hash'})
        with self.assertRaisesRegex(ValueError,'Conflicting hashes'):canonical_inputs({path:'first',canonical:'second'})

    def test_provider_data_binding_not_ambiguous_with_payload_work(self):
        self.c.execute('UPDATE symbol_occurrences SET strategy="external_source",provider_id="ccl",symbol_kind="STT_OBJECT" WHERE id="o0"')
        d.add_work(self.c,'provider_binding','o0',['o0'],'o0')
        d.add_work(self.c,'extract_payload','content',['o0'],'o0')
        self.c.commit();task=self.task();task['originals']=task['originals'][:1]
        self.assertEqual(w.plan(self.c,task)['work_kind'],'provider_binding')

    def test_decisions_append_only(self):
        self.shared()
        with self.assertRaises(sqlite3.IntegrityError):self.c.execute('DELETE FROM equivalence_decisions')
