import copy
import json
import unittest
from unittest.mock import patch
import sqlite3
import adapter
import registry as r
import workflow as w
import test_workflow as fixtures

class AdapterTests(unittest.TestCase):
    setUp=fixtures.WorkflowTests.setUp
    def read(self):
        with adapter.RegistrySnapshot(self.db) as s:
            return copy.deepcopy(s.ready['functions']),copy.deepcopy(s.pending['functions']),s.guard
    def commit(self,ready,pending,guard,**kw):
        return adapter.commit_snapshot(ready,pending,guard,library=self.lib,db=self.db,actor='fixture',reason='Validated fixture',**kw)
    def test_snapshot_deduplicates_source_maps_and_roundtrips(self):
        with adapter.RegistrySnapshot(self.db) as s:
            self.assertIs(s.ready['functions'][0]['sources'],s.pending['functions'][0]['sources'])
            self.assertEqual(s.provenance()['guard'],s.guard)
            self.assertEqual(s.ready['functions'][0],self.entries['a'])
    def test_noop_still_checks_evidence_and_writes_nothing(self):
        ready,pending,guard=self.read();before=r.digest(self.db);called=[]
        result=self.commit(ready,pending,guard,precommit_guard=lambda:called.append(True))
        self.assertTrue(result['no_op']);self.assertEqual(called,[True]);self.assertEqual(before,r.digest(self.db))
    def test_changed_rows_only_backup_and_metadata_only_audit(self):
        ready,pending,guard=self.read();ready[0]['domain']='Reviewed bounded fixture update'
        result=self.commit(ready,pending,guard,request_id='changed')
        self.assertEqual(result['changed'],1)
        with r.connect(result['backup']) as c:self.assertEqual(c.execute('SELECT count(*) FROM journal').fetchone()[0],0)
        with r.connect(self.db) as c:self.assertEqual(c.execute('SELECT count(*) FROM journal').fetchone()[0],1)
        ready,pending,guard=self.read();result=self.commit(ready,pending,guard,metadata={'ready':{'new_metadata':['kept',True,None]}},request_id='metadata')
        self.assertEqual(result['metadata_changed'],['ready'])
        with adapter.RegistrySnapshot(self.db) as s:
            self.assertEqual(s.ready['new_metadata'],['kept',True,None])
            self.assertEqual(s.c.execute('SELECT count(*) FROM journal').fetchone()[0],1)
    def test_missing_keys_demotion_and_concurrency_fail_closed(self):
        ready,pending,guard=self.read()
        with self.assertRaises(ValueError):self.commit([],pending,guard)
        demoted=dict(ready[0],portable_ready=False,validation_sha256='new-proof')
        with self.assertRaises(ValueError):self.commit([],pending+[demoted],guard)
        w.operate(self.db,self.lib,{'request_id':'concurrent','actor':'fixture','operations':[{'kind':'assign','original_elf_sha256':'elf','mangled':'a','expected_revision':0,'reason':'concurrent fixture','value':'owner'}]},False)
        with self.assertRaises(ValueError):self.commit(ready,pending,guard)
    def test_midwrite_failure_rolls_back_and_keeps_backup(self):
        ready,pending,guard=self.read();ready[0]['domain']='changed'
        c=sqlite3.connect(self.db);c.execute("CREATE TRIGGER fail_new_journal BEFORE INSERT ON journal BEGIN SELECT RAISE(ABORT,'fixture rejection'); END");c.commit();c.close()
        with adapter.RegistrySnapshot(self.db) as s:guard=s.guard
        before=r.digest(self.db)
        with self.assertRaises(Exception):self.commit(ready,pending,guard)
        self.assertEqual(before,r.digest(self.db))
        self.assertTrue(list((self.db.parent/'admission-history').glob('*.sqlite')))

    def snapshot_receipt(self):
        # Synthetic authorization fixture, never an actual VM/firmware claim.
        path=self.root/'snapshot-rollback.json'
        path.write_text(json.dumps({'backup_policy':'one rollback snapshot; no additional full copies',
            'snapshot':{'verified':True,'vmid':101,'host':'192.168.50.2',
                'name':'pre-publication-redesign-20261113',
                'includes_pvdata_working_disk':'pvdata/vm-101-disk-5',
                'disk_snapshot_count':8,'ram':False,'external_CT126_included':False,
                'guest_filesystems':'freeze/snapshot/thaw completed'}}))
        return path,{'rollback_snapshot':path,'rollback_snapshot_sha256':r.digest(path)}

    def test_explicit_snapshot_no_copy_and_exact_audit_binding(self):
        path,options=self.snapshot_receipt();ready,pending,guard=self.read()
        ready[0]['domain']='Snapshot-backed bounded fixture update'
        original=sqlite3.connect;opened=[]
        allowed={str(self.db.resolve()),self.db.resolve().as_uri()+'?mode=ro',self.db.resolve().as_uri()+'?mode=rw'}
        def no_backup(database,*args,**kw):
            opened.append(str(database));self.assertIn(str(database),allowed)
            return original(database,*args,**kw)
        with patch.object(adapter.sqlite3,'connect',side_effect=no_backup):
            result=self.commit(ready,pending,guard,request_id='snapshot-change',**options)
        self.assertTrue(opened);self.assertIsNone(result['backup']);self.assertIsNone(result['backup_sha256'])
        self.assertFalse((self.db.parent/'admission-history').exists())
        rollback=result['rollback'];self.assertEqual(rollback['receipt']['sha256'],r.digest(path))
        self.assertTrue(rollback['post_restore_graph_reconciliation_required'])
        with r.connect(self.db) as c:
            request=c.execute("SELECT digest,result FROM requests WHERE request_id='snapshot-change'").fetchone()
            bindings=json.loads(c.execute('SELECT bindings FROM journal').fetchone()[0])
        self.assertEqual(json.loads(request['result'])['rollback'],rollback)
        self.assertEqual(bindings['rollback'],rollback);self.assertIsNone(bindings['backup_sha256'])
        payload={'changed_keys':[('elf','a')],'metadata_changes':{},'operation_metadata':{},
                 'demotion_manifests':{},'expected_guard':guard,'backup_sha256':None,'rollback':rollback}
        self.assertEqual(request['digest'],__import__('hashlib').sha256(r.encode(payload).encode()).hexdigest())

    def test_snapshot_noop_still_checks_source_guard_without_copy(self):
        _,options=self.snapshot_receipt();ready,pending,guard=self.read();calls=[]
        result=self.commit(ready,pending,guard,precommit_guard=lambda:calls.append(True),**options)
        self.assertTrue(result['no_op']);self.assertEqual(calls,[True]);self.assertIsNone(result['backup'])
        self.assertFalse((self.db.parent/'admission-history').exists())

    def test_snapshot_receipt_failures_and_ambiguous_mode_do_not_write(self):
        path,options=self.snapshot_receipt();ready,pending,guard=self.read();ready[0]['domain']='new'
        before=r.digest(self.db)
        with self.assertRaises(ValueError):self.commit(ready,pending,guard,rollback_snapshot=path)
        with self.assertRaises(ValueError):self.commit(ready,pending,guard,backup_dir=self.root/'extra',**options)
        with self.assertRaises(ValueError):self.commit(ready,pending,guard,**dict(options,rollback_snapshot_sha256='0'*64))
        valid=json.loads(path.read_text())
        for key,value in [('verified',False),('vmid',125),('name','other-snapshot'),
                          ('includes_pvdata_working_disk','wrong-disk'),('disk_snapshot_count',1),
                          ('guest_filesystems','not quiesced'),('external_CT126_included',True)]:
            document=copy.deepcopy(valid);document['snapshot'][key]=value;path.write_text(json.dumps(document))
            with self.subTest(key=key),self.assertRaises(ValueError):
                self.commit(ready,pending,guard,rollback_snapshot=path,rollback_snapshot_sha256=r.digest(path))
            self.assertEqual(r.digest(self.db),before)
        self.assertFalse((self.db.parent/'admission-history').exists())

    def test_snapshot_precommit_and_receipt_races_roll_back(self):
        path,options=self.snapshot_receipt();ready,pending,guard=self.read();ready[0]['domain']='new'
        before=r.digest(self.db);calls=[]
        def tamper_after_writes():
            calls.append(True)
            if len(calls)==2:path.write_text('receipt changed after row updates')
        with self.assertRaises(ValueError):self.commit(ready,pending,guard,precommit_guard=tamper_after_writes,**options)
        self.assertEqual(len(calls),2);self.assertEqual(r.digest(self.db),before)
        self.assertFalse((self.db.parent/'admission-history').exists())

    def test_snapshot_preserves_existing_admission_and_concurrency_guards(self):
        _,options=self.snapshot_receipt();ready,pending,guard=self.read()
        with self.assertRaises(ValueError):self.commit([],pending,guard,**options)
        with self.assertRaises(ValueError):self.commit(ready,pending,'stale-guard',**options)
        self.assertFalse((self.db.parent/'admission-history').exists())

if __name__=='__main__':unittest.main()
