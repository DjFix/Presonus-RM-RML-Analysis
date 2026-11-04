"""Synthetic registry/API component tests; no real firmware/proof readiness credit."""
from pathlib import Path
import copy,hashlib,importlib.util,json,shutil,sqlite3,sys,tempfile,unittest,ast
R=Path(__file__).resolve().parents[3];W=R/'temp/test-work/registry-enrichment';W.mkdir(parents=True,exist_ok=True)
sys.path[:0]=[str(R/'dependency-graph'),str(R/'uc-library/tools/registry')]
import adapter,registry as reg,schema,workflow,catalog

def load(name,path,root):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.ROOT=root;return m

class CandidateTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=W);self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.lib=self.root/'uc-library';self.lib.mkdir();self.db=self.root/'operational.sqlite';self.elf='a'*64;self.name='_ZN3Foo3barEv'
  paths={}
  for status in ['ready','pending']:
   entries=[{'original_elf_sha256':self.elf,'mangled':self.name,'original_address':100,'original_size':8,'sources':{},'validation':'synthetic-proof-only.json','validation_sha256':'0'*64,'portable_ready':True,'domain':'Synthetic registry fixture only; no firmware/ABI evidence'}] if status=='ready' else []
   p=self.root/(status+'.json');p.write_text(json.dumps({'functions':entries}));paths[status]=p
  reg.capture(paths,self.root/'snapshots');reg.import_snapshots(self.root/'snapshots',self.root/'baseline.sqlite');workflow.working_copy(self.root/'baseline.sqlite',self.db);schema.upgrade(self.db,self.root/'before-upgrade.sqlite',True)
  with sqlite3.connect(self.db) as c:
   c.executescript(catalog.SCHEMA)
   c.execute('INSERT INTO catalog_symbols VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',('fixture-anchor',self.elf,'client','synthetic',self.name,'Foo::bar()',100,8,'1','STT_FUNC','STB_GLOBAL','application-or-other'));c.commit()
  self.point(self.db);self.new=load('new_enrich_fixture',R/'uc-library/tools/recovery/select_context.py',self.root)
  self.task={'task_id':'fixture','objective':'Synthetic metadata/API component only','namespace':'Foo','mode':'audit','owned_files':[],'targets':[{'original_elf_sha256':self.elf,'mangled':self.name,'address':100,'size':8}]}
 def point(self,db):
  p=self.lib/'validation/registry-sqlite/ACTIVE.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps({'database':{'absolute_path':str(db)}}))
 def test_default_and_provided_are_identical(self):
  before=reg.digest(self.db);expected=self.new.enrich(self.task);default=self.new.enrich(self.task)
  with adapter.snapshot(self.lib) as view:
   shared=self.new.enrich(self.task,view);self.assertTrue(view.c.in_transaction);self.assertEqual(shared,self.new.enrich(self.task,view))
  self.assertEqual(expected,default);self.assertEqual(expected,shared);self.assertEqual(reg.digest(self.db),before)
 def test_read_only_audit_and_research_no_writes(self):
  with adapter.snapshot(self.lib) as view:
   for mode in ['audit','research']:
    task=dict(self.task,mode=mode);self.assertEqual(self.new.enrich(task),self.new.enrich(task,view))
 def test_missing_original_scope_and_range_keep_rejecting(self):
  variants=[];bad=copy.deepcopy(self.task);bad['targets'][0]['mangled']='missing';variants.append(bad);variants.append(dict(self.task,namespace='Other'))
  # Address/size mismatch is checked from target when no admitted record exists.
  bad=copy.deepcopy(self.task);bad['targets'][0]['anchor']='foreign-anchor';variants.append(bad)
  for task in variants:
   with self.subTest(task=task),adapter.snapshot(self.lib) as view:
    with self.assertRaises(Exception):self.new.enrich(task)
    with self.assertRaises(Exception):self.new.enrich(task,view)
  with sqlite3.connect(self.db) as c:c.execute('DELETE FROM records');c.commit()
  bad=copy.deepcopy(self.task);bad['targets'][0]['address']=101
  with adapter.snapshot(self.lib) as view:
   with self.assertRaises(Exception):self.new.enrich(bad)
   with self.assertRaises(Exception):self.new.enrich(bad,view)
 def test_task_validation_kept(self):
  with adapter.snapshot(self.lib) as view:
   for task in [dict(self.task,task_id='invalid task'),dict(self.task,mode='reconstruct'),dict(self.task,owned_files=['uc-library/src/a.cpp'])]:
    with self.subTest(task=task),self.assertRaises(Exception):self.new.enrich(task,view)
 def test_source_contract_rechecked_on_each_call(self):
  p=self.root/'contract.json';p.write_text('{}');task=dict(self.task,mode='reconstruct',owned_files=['uc-library/src/a.cpp'],reconstruction_contract={'path':'contract.json','sha256':reg.digest(p)})
  with adapter.snapshot(self.lib) as view:
   with self.assertRaisesRegex(Exception,'Execution-boundary review required'):self.new.enrich(task,view)
   p.write_text('{"changed":true}')
   with self.assertRaisesRegex(Exception,'Stale evidence'):self.new.enrich(task,view)
   self.assertTrue(view.c.in_transaction)
 def test_foreign_closed_and_inactive_views_rejected(self):
  foreign=self.root/'foreign.sqlite';shutil.copy2(self.db,foreign)
  with adapter.RegistrySnapshot(foreign) as view:
   with self.assertRaisesRegex(Exception,'foreign'):self.new.enrich(self.task,view)
  with adapter.snapshot(self.lib) as view:pass
  with self.assertRaisesRegex(Exception,'closed'):self.new.enrich(self.task,view)
  with adapter.snapshot(self.lib) as view:
   view.c.rollback()
   with self.assertRaisesRegex(Exception,'live transaction'):self.new.enrich(self.task,view)
 def test_pointer_change_rejected(self):
  foreign=self.root/'foreign.sqlite';shutil.copy2(self.db,foreign)
  with adapter.snapshot(self.lib) as view:
   self.point(foreign)
   with self.assertRaisesRegex(Exception,'pointer changed'):self.new.enrich(self.task,view)
 def test_closed_setup_fresh_barrier_sees_record_mutation_no_leak(self):
  with adapter.snapshot(self.lib) as setup:old=self.new.enrich(self.task,setup)
  with sqlite3.connect(self.db) as c:
   row=c.execute('SELECT id,metadata FROM records').fetchone();metadata=json.loads(row[1]);metadata['domain']='New synthetic metadata at fresh barrier';c.execute('UPDATE records SET metadata=? WHERE id=?',(json.dumps(metadata),row[0]));c.commit()
  with adapter.snapshot(self.lib) as barrier:new=self.new.enrich(self.task,barrier)
  self.assertNotEqual(old['registry_guard'],new['registry_guard']);self.assertNotEqual(old['originals'],new['originals']);self.assertEqual(new,self.new.enrich(self.task))
  with self.assertRaises(Exception):self.new.enrich(self.task,setup)

 def test_real_batch_barrier_reopens_and_detects_mutation(self):
  from context_batch import check_registry_records
  with adapter.snapshot(self.lib) as view:request=self.new.enrich(self.task,view)
  check_registry_records(self.new,[request],'changed')
  with sqlite3.connect(self.db) as c:
   row=c.execute('SELECT id,metadata FROM records').fetchone();metadata=json.loads(row[1]);metadata['domain']='Changed after first barrier';c.execute('UPDATE records SET metadata=? WHERE id=?',(json.dumps(metadata),row[0]));c.commit()
  with self.assertRaisesRegex(Exception,'changed'):check_registry_records(self.new,[request],'changed')
  fresh=self.new.enrich(self.task)
  check_registry_records(self.new,[fresh],'changed')
  with adapter.snapshot(self.lib) as view:self.assertTrue(view.c.in_transaction)

if __name__=='__main__':unittest.main()
