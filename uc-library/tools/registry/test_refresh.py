import json
import unittest
import pathlib
import sqlite3
import registry as r
import workflow as w
import schema
import refresh
import test_workflow as fixtures

class RefreshTests(unittest.TestCase):
    setUp=fixtures.WorkflowTests.setUp
    request=fixtures.WorkflowTests.request
    def test_history_maps_original_keys_and_preserves_new_classification(self):
        w.operate(self.db,self.lib,self.request({'kind':'assign','value':'meaningful-fixture-owner'}),False)
        # Deliberately shift IDs in a new immutable baseline, while keeping keys.
        paths={}
        for status,name in [('ready','a'),('pending','b')]:
            paths[status]=self.root/('new-'+status+'.json')
            paths[status].write_text(json.dumps({'functions':[self.entries[name]]}))
        r.capture({'pending':paths['pending'],'ready':paths['ready']},self.root/'new-snapshots')
        r.import_snapshots(self.root/'new-snapshots',self.root/'new-baseline')
        target=self.root/'new-working';w.working_copy(self.root/'new-baseline',target);schema.upgrade(target,self.root/'new-backup',True)
        before=r.digest(target);refresh.transfer(self.db,target);self.assertEqual(before,r.digest(target))
        with r.connect(target) as c:records_before=[tuple(x) for x in c.execute('SELECT * FROM records ORDER BY id')]
        refresh.transfer(self.db,target,True)
        with r.connect(target) as c:
            self.assertEqual(records_before,[tuple(x) for x in c.execute('SELECT * FROM records ORDER BY id')])
            row=c.execute('SELECT r.mangled,w.assignment,w.revision FROM records r JOIN work_state w ON r.id=w.record_id WHERE r.mangled="b"').fetchone()
            self.assertEqual(tuple(row),('b','meaningful-fixture-owner',1))
            self.assertEqual(c.execute('SELECT count(*) FROM journal').fetchone()[0],1)
            self.assertTrue(any(x[0]!=x[1] for x in c.execute('SELECT old_record_id,new_record_id FROM generation_identity')))
        with self.assertRaises(ValueError):refresh.transfer(self.db,target,True)

if __name__=='__main__':unittest.main()
