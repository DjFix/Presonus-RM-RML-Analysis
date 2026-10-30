import copy
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch
import registry as r
import workflow as w
import schema

ROOT=pathlib.Path(__file__).resolve().parents[3]

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        base=ROOT/'temp/registry-tests';base.mkdir(parents=True,exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=base);self.addCleanup(self.tmp.cleanup)
        self.root=pathlib.Path(self.tmp.name);self.lib=self.root/'library';self.lib.mkdir()
        def put(name,value):
            path=self.lib/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value));return r.digest(path)
        self.put=put
        p=self.lib/'t.cpp';p.write_text('int f() {return 1;}\n');self.sources={'t.cpp':r.digest(p)}
        put('validation/formatting.json',{'format_check_passed':True,'files':self.sources})
        put('validation/integration.json',{'ctest_passed':True,'files':self.sources})
        for role in ('client','server'):
            put('recovered-all/'+role+'/manifest.json',{'sha256':'elf'})
            put('recovered-all/'+role+'/symbols.json',[{'mangled':n,'address':i,'kind':'STT_FUNC','section':1,'size':4} for i,n in enumerate(('a','b','c'))])
        self.proof=put('proof.json',{'cpp_differential_passed':True,'compiled_mangled_names_matched':True,'mangled_names':['a','b','c'],'original_elf_sha256':'elf'})
        self.entries={}
        paths={}
        for status,name in [('ready','a'),('pending','b')]:
            entry={'original_elf_sha256':'elf','mangled':name,'sources':self.sources,'validation':'proof.json','validation_sha256':self.proof,'portable_ready':status=='ready','domain':'bounded fixture','cpp_compiled':True,'mangling_namespace_checked':True}
            self.entries[name]=entry
            paths[status]=self.root/(status+'.json');paths[status].write_text(json.dumps({'functions':[entry]}))
        r.capture(paths,self.root/'snapshots');r.import_snapshots(self.root/'snapshots',self.root/'baseline')
        self.db=self.root/'work';w.working_copy(self.root/'baseline',self.db)
        schema.upgrade(self.db,self.root/'before-upgrade',True)
    def request(self,op,name='req'):
        return {'request_id':name,'actor':'fixture','operations':[dict(original_elf_sha256='elf',mangled='b',expected_revision=0,reason='fixture evidence',**op)]}
    def test_preflight_assignment_idempotence_revision_and_rollback(self):
        payload=self.request({'kind':'assign','value':'owner'})
        before=r.digest(self.db);w.operate(self.db,self.lib,payload);self.assertEqual(before,r.digest(self.db))
        w.operate(self.db,self.lib,payload,False)
        self.assertTrue(w.operate(self.db,self.lib,payload,False)['idempotent_replay'])
        bad=self.request({'kind':'block','value':'missing'},'bad')
        with self.assertRaises(ValueError):w.operate(self.db,self.lib,bad,False)
        self.assertEqual(len(w.query(self.db,'audit',{})),1)
        payload=self.request({'kind':'block','value':'missing'},'batch')
        payload['operations'][0]['expected_revision']=1
        payload['operations'].append(dict(original_elf_sha256='elf',mangled='a',expected_revision=99,kind='assign',value='x',reason='stale revision'))
        before=r.digest(self.db)
        with self.assertRaises(ValueError):w.operate(self.db,self.lib,payload,False)
        self.assertEqual(before,r.digest(self.db))
    def test_promotion_demotion_and_stale_proof(self):
        entry=dict(self.entries['b'],portable_ready=True)
        payload=self.request({'kind':'classify','target':'ready','entry':entry,'previous_validation_sha256':self.proof})
        w.operate(self.db,self.lib,payload,False)
        self.assertEqual(w.query(self.db,'counts',{})['classifications'],[{'status':'ready','count':2}])
        pending=dict(entry,portable_ready=False)
        sha=self.put('pending-proof.json',{'functions':[pending]})
        pending.update(validation='pending-proof.json',validation_sha256=sha)
        op={'kind':'classify','target':'pending','entry':pending,'previous_validation_sha256':self.proof}
        payload=self.request(op,'demote');payload['operations'][0]['expected_revision']=1
        w.operate(self.db,self.lib,payload,False)
        self.assertEqual(len(w.query(self.db,'query',{'status':'pending'})),1)
        entry['validation_sha256']='wrong'
        payload=self.request({'kind':'classify','target':'ready','entry':entry,'previous_validation_sha256':sha},'stale');payload['operations'][0]['expected_revision']=2
        with self.assertRaises(ValueError):w.operate(self.db,self.lib,payload,False)
        self.assertEqual(len(w.query(self.db,'audit',{})),2)
    def test_stage_and_hardware_rejection(self):
        sha=self.put('stage.json',{'original_elf_sha256':'elf','mangled':'b','cpp_compiled':True})
        payload=self.request({'kind':'stage','stage':'compiled','proof':'stage.json','proof_sha256':sha,'domain':'fixture compile only'})
        w.operate(self.db,self.lib,payload,False)
        self.assertEqual(w.query(self.db,'counts',{})['stages'],[{'stage':'compiled','count':1}])
        payload=self.request({'kind':'stage','stage':'hardware','proof':'stage.json','proof_sha256':sha,'domain':'none'},'hardware');payload['operations'][0]['expected_revision']=1
        with self.assertRaises(ValueError):w.operate(self.db,self.lib,payload,False)
    def test_synthetic_hardware_evidence_only_and_core_path_guard(self):
        auth=self.put('fixture-authorization.json',{'synthetic':'unit fixture only; no device authorization'})
        observation=self.put('fixture-observation.json',{'synthetic':'no device IO'})
        proof={'original_elf_sha256':'elf','mangled':'b','hardware_validation_passed':True,'hardware_verified':True,'device_identifier':'synthetic-unit-fixture',
               'hardware_authorization':{'path':'fixture-authorization.json','sha256':auth},
               'hardware_observations':[{'path':'fixture-observation.json','sha256':observation}]}
        sha=self.put('hardware-fixture.json',proof)
        payload=self.request({'kind':'stage','stage':'hardware','proof':'hardware-fixture.json','proof_sha256':sha,'domain':'Synthetic schema test only; no hardware evidence or device IO'})
        w.operate(self.db,self.lib,payload,False)
        self.assertEqual(w.query(self.db,'query',{'mangled':'b'})[0]['status'],'pending')
        entry=dict(self.entries['b'],portable_ready=True,repository_sources={'outside-core.cpp':'hash'})
        payload=self.request({'kind':'classify','target':'ready','entry':entry,'previous_validation_sha256':self.proof},'core-guard')
        payload['operations'][0]['expected_revision']=1
        with self.assertRaises(ValueError):w.operate(self.db,self.lib,payload,False)

    def test_stale_source_and_append_only_journal(self):
        payload=self.request({'kind':'classify','target':'ready','entry':dict(self.entries['b'],portable_ready=True),'previous_validation_sha256':self.proof})
        (self.lib/'t.cpp').write_text('changed')
        with self.assertRaises(ValueError):w.operate(self.db,self.lib,payload,False)
        w.operate(self.db,self.lib,self.request({'kind':'assign','value':'x'}),False)
        c=w.sqlite3.connect(self.db)
        self.addCleanup(c.close)
        with self.assertRaises(w.sqlite3.DatabaseError):c.execute('DELETE FROM journal')
    def test_post_mutation_journal_failure_rolls_back_orm_and_raw_sets(self):
        # Fail only after Record/WorkState/request/evidence writes and raw source
        # sets have happened; this exercises the shared transaction, not preflight.
        c=w.sqlite3.connect(self.db)
        c.execute("CREATE TRIGGER reject_journal BEFORE INSERT ON journal BEGIN SELECT RAISE(ABORT,'injected post-mutation failure'); END")
        c.commit();c.close()
        with r.connect(self.db) as c:before=schema.fingerprint(c)
        extra=self.lib/'extra.cpp';extra.write_text('int extra() {return 2;}\n')
        expanded=dict(self.sources,**{'extra.cpp':r.digest(extra)})
        self.put('validation/formatting.json',{'format_check_passed':True,'files':expanded})
        self.put('validation/integration.json',{'ctest_passed':True,'files':expanded})
        entry=dict(self.entries['b'],portable_ready=True,sources=expanded)
        payload=self.request({'kind':'classify','target':'ready','entry':entry,'previous_validation_sha256':self.proof},'midwrite')
        with self.assertRaises(Exception):w.operate(self.db,self.lib,payload,False)
        with r.connect(self.db) as c:self.assertEqual(schema.fingerprint(c),before)

    def test_newer_schema_race_rejected_inside_locked_transaction(self):
        original=w.orm.Unit
        def migrated_before_lock(db,write=False):
            c=w.sqlite3.connect(db)
            c.execute("UPDATE alembic_version SET version_num='9999_future'")
            c.commit();c.close()
            return original(db,write)
        with r.connect(self.db) as c:
            before={name:value for name,value in schema.fingerprint(c).items() if name!='alembic_version'}
        with patch.object(w.orm,'Unit',migrated_before_lock):
            with self.assertRaises(ValueError):w.operate(self.db,self.lib,self.request({'kind':'assign','value':'must-not-write'}),False)
        c=w.sqlite3.connect(self.db);c.row_factory=w.sqlite3.Row
        after={name:value for name,value in schema.fingerprint(c).items() if name!='alembic_version'}
        c.close();self.assertEqual(before,after)

    def test_legacy_null_role_and_historical_formatting_provenance(self):
        entry=dict(self.entries['b'],role=None,portable_ready=True,formatting_sha256='historical')
        payload=self.request({'kind':'classify','target':'ready','entry':entry,'previous_validation_sha256':self.proof},'legacy-parity')
        w.operate(self.db,self.lib,payload,False)
        with r.connect(self.db) as c:
            row=c.execute('SELECT * FROM records WHERE mangled="b"').fetchone()
            admitted=r.restored(c,row)
            self.assertEqual(admitted['formatting_sha256'],r.digest(self.lib/'validation/formatting.json'))
            self.assertIs(admitted['original_function_verified'],False)
        self.assertEqual(payload['operations'][0]['entry']['formatting_sha256'],'historical')

    def test_new_admission_requires_absent_key_and_full_evidence(self):
        entry=dict(self.entries['b'],mangled='c',portable_ready=True)
        payload=self.request({'kind':'admit','target':'ready','entry':entry},'new')
        payload['operations'][0].update(mangled='c',expected_revision=-1)
        before=r.digest(self.db)
        w.operate(self.db,self.lib,payload)
        self.assertEqual(before,r.digest(self.db))
        w.operate(self.db,self.lib,payload,False)
        self.assertEqual(len(w.query(self.db,'query',{'mangled':'c'})),1)
        payload['request_id']='duplicate'
        with self.assertRaises(ValueError):w.operate(self.db,self.lib,payload,False)

    def test_partial_database_rejected(self):
        p=self.root/'partial';w.sqlite3.connect(p).close()
        with self.assertRaises(ValueError):r.connect(p)

if __name__=='__main__':unittest.main()
