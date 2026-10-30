"""Administrative metadata preparation fixtures; never native validation."""
import json
import pathlib
import shutil
import unittest
import registry as r
import adapter
import workflow as w
import prepare_cycle_admin_context as prep
import test_workflow as fixtures

class AdminContextTests(unittest.TestCase):
    setUp=fixtures.WorkflowTests.setUp
    def inputs(self):
        header=self.lib/prep.HEADER;header.parent.mkdir(parents=True);header.write_text('// synthetic header fixture\n')
        (self.lib/'CMakeLists.txt').write_text('# synthetic build context\n');(self.lib/'cmake').mkdir();(self.lib/'cmake/ProductionSourceGroups.cmake').write_text('# fixture partition context\n')
        files=dict(self.sources,**{prep.HEADER:r.digest(header)});self.put('validation/formatting.json',{'format_check_passed':True,'files':files})
        ready=dict(self.entries['a'],sources=dict(self.sources,**{'CMakeLists.txt':r.digest(self.lib/'CMakeLists.txt')}))
        pending=dict(self.entries['b'],sources=dict(files,**{'CMakeLists.txt':r.digest(self.lib/'CMakeLists.txt')}))
        sha=self.put('pending-root.json',{'functions':[pending]});pending.update(validation='pending-root.json',validation_sha256=sha)
        payload={'request_id':'fixture-context','actor':'fixture','operations':[{'kind':'classify','target':status,'original_elf_sha256':'elf','mangled':name,'entry':entry,'previous_validation_sha256':self.proof,'expected_revision':0,'reason':'Synthetic context fixture setup'} for name,status,entry in [('a','ready',ready),('b','pending',pending)]]}
        w.operate(self.db,self.lib,payload,False)
        archive=self.lib/'candidate/archive';archive.mkdir(parents=True);rules={}
        for name in prep.ALLOWED:
            target=archive/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(self.lib/name,target);rules[name]={'archive':str(target.relative_to(self.lib)),'sha256':r.digest(target),'role':'historical_build_or_format_producer_context'}
        path=archive/'ARCHIVES.json';path.write_text(json.dumps({'files':rules}));return path
    def test_only_admin_fields_change_and_real_header_rows_are_excluded(self):
        archives=self.inputs();before=r.digest(self.db);out=self.lib/'candidate/prepared'
        result=prep.prepare(self.lib,archives,out,self.db,expected_header_keys=1)
        self.assertEqual(before,r.digest(self.db));self.assertEqual(result['counts'],{'ready_context':1,'pending_context':1,'ready_admin_only':1,'pending_admin_only':0,'header_replay_required':1})
        ready=json.loads((out/'ready-all-context.json').read_text())['functions'][0]
        pending=json.loads((out/'pending-all-context.json').read_text())['functions'][0]
        with adapter.RegistrySnapshot(self.db) as current:
            oldready=current.ready['functions'][0];oldpending=current.pending['functions'][0]
            self.assertEqual(ready['validation_sha256'],oldready['validation_sha256'])
            self.assertEqual(ready['domain'],oldready['domain']);self.assertEqual(pending['sources'][prep.HEADER],oldpending['sources'][prep.HEADER])
            self.assertEqual(pending['sources']['t.cpp'],oldpending['sources']['t.cpp'])
            membership=json.loads((self.lib/pending['validation']).read_text())['functions'][0]
            self.assertEqual(membership['validation_sha256'],oldpending['validation_sha256'])
            self.assertEqual(membership['sources'],pending['sources'])
    def test_implementation_path_cannot_be_classified_as_historical(self):
        archives=self.inputs();data=json.loads(archives.read_text());data['files'][prep.HEADER]={'archive':'irrelevant','sha256':'irrelevant'};archives.write_text(json.dumps(data))
        before=r.digest(self.db)
        with self.assertRaises(ValueError):prep.prepare(self.lib,archives,self.lib/'candidate/rejected',self.db,1)
        self.assertEqual(before,r.digest(self.db))

if __name__=='__main__':unittest.main()
