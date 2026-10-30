import copy
import json
import unittest
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

if __name__=='__main__':unittest.main()
