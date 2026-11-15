"""Synthetic coordinator recovery tests; no firmware, graph or live claims."""
from contextlib import ExitStack, nullcontext
from pathlib import Path
import copy,json,sqlite3,tempfile,types,unittest
from unittest.mock import patch
import context_batch
from context_runtime import ContextError

class StopAfterClaims(Exception):pass
class FakeRunner:
    def __init__(self,*args):pass
    def close(self):pass
class StopValidator:
    def __init__(self,*args):pass
    def validate(self,*args):pass
    def finish(self):raise StopAfterClaims()
    def close(self):pass

class PrefreezeResume(unittest.TestCase):
    def setUp(self):
        scratch=Path(__file__).resolve().parents[1]/'temp/test-work';scratch.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=scratch);self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.out=self.root/'temp/recovery-work/batch'
        self.task={'task_id':'task_a','owned_files':['uc-library/src/a.cpp'],'originals':[]}
        (self.root/'task.json').write_text(json.dumps(self.task));(self.root/'manifest.json').write_text('{"tasks":["task.json"]}')
        self.database=self.root/'claims.sqlite';c=sqlite3.connect(self.database)
        c.execute('create table work_claims(id integer primary key,work_item_id text,owner text,packet_path text,state text)');c.commit();c.close()
        self.operator=types.SimpleNamespace(ROOT=self.root,adapter=types.SimpleNamespace(snapshot=lambda *args:nullcontext(None)),enrich=lambda task,view:copy.deepcopy(task),ensure_fresh=lambda:None)
        self.claim_calls=0
    def connection(self):
        c=sqlite3.connect(self.database);c.row_factory=sqlite3.Row;return c,{'database':'claims.sqlite'}
    def plan(self,c,t):return {'work_item_id':'work-a','covered_occurrences':[]}
    def claim(self,root,t,packet):
        self.assertTrue((self.out/'FROZEN.json').is_file())
        self.claim_calls+=1;c=sqlite3.connect(self.database);c.execute('insert into work_claims values(1,?,?,?,"active")',('work-a',t['task_id'],packet));c.commit();c.close()
        return dict(t,work_binding={'work_item_id':'work-a','claim_id':1,'claim_owner':t['task_id'],'claim_packet':packet,'covered_occurrences':[]})
    def rows(self):
        c=sqlite3.connect(self.database);rows=c.execute('select * from work_claims').fetchall();c.close();return rows
    def call(self,resume=False,refresh=None):
        with ExitStack() as s:
            s.enter_context(patch.object(context_batch,'validate_tasks'))
            s.enter_context(patch.object(context_batch,'locked',side_effect=lambda *a,**k:nullcontext()))
            s.enter_context(patch.object(context_batch,'memgraph_uri',return_value='bolt://unused'))
            s.enter_context(patch.object(context_batch,'capture_inputs',return_value={'active':{'state_sha256':'a'*64},'files':{}}))
            s.enter_context(patch('dedup_work.active_index',side_effect=lambda *a:self.connection()))
            s.enter_context(patch('dedup_work.plan',side_effect=self.plan))
            s.enter_context(patch('dedup_work.claim_task',side_effect=self.claim))
            s.enter_context(patch('dedup_work.validate_claim'))
            s.enter_context(patch('context_work_batch.BatchWorkValidator',StopValidator))
            if refresh is not None:s.enter_context(patch.object(self.operator,'ensure_fresh',side_effect=refresh))
            return context_batch.run.__wrapped__(self.operator,'manifest.json','temp/recovery-work/batch',resume=resume,runner_factory=FakeRunner)
    def fail_before_freeze(self):
        with self.assertRaisesRegex(ContextError,'refresh failed'):
            self.call(refresh=ContextError('refresh failed'))
        self.assertFalse((self.out/'FROZEN.json').exists());self.assertEqual(self.rows(),[])
    def test_actual_early_refresh_failure_then_same_output_first_claim(self):
        self.fail_before_freeze()
        with self.assertRaises(StopAfterClaims):self.call(resume=True)
        self.assertEqual(self.claim_calls,1);self.assertEqual(len(self.rows()),1)
        self.assertTrue((self.out/'FROZEN.json').is_file())
        request=json.loads((self.out/'packets/task_a/request.json').read_text());self.assertEqual(request['work_binding']['claim_id'],1)
    def test_matching_existing_owner_claim_reused_without_reclaim(self):
        self.fail_before_freeze();c=sqlite3.connect(self.database);c.execute('insert into work_claims values(1,"work-a","task_a","temp/recovery-work/batch/packets/task_a","active")');c.commit();c.close();before=self.rows()
        with self.assertRaises(StopAfterClaims):self.call(resume=True)
        self.assertEqual(self.rows(),before);self.assertEqual(self.claim_calls,0)
    def test_foreign_claim_is_still_rejected(self):
        self.fail_before_freeze();c=sqlite3.connect(self.database);c.execute('insert into work_claims values(1,"work-a","foreign","another/packet","active")');c.commit();c.close();before=self.rows()
        with self.assertRaisesRegex(ContextError,'foreign claim'):self.call(resume=True)
        self.assertEqual(self.rows(),before);self.assertEqual(self.claim_calls,0)
    def test_missing_freeze_with_prepared_artifact_rejects_before_refresh(self):
        for artifact in ['packets/task_a/context.json','packets/task_a/request.json','SNAPSHOT.json','snapshot/file','BATCH_DISPATCH.json','IMAGES.json','unexpected.txt']:
            with self.subTest(artifact=artifact):
                self.out.mkdir(parents=True,exist_ok=True);p=self.out/artifact;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('{}')
                with patch.object(self.operator,'ensure_fresh') as refresh:
                    with self.assertRaisesRegex(ContextError,'unsafe/partial'):self.call(resume=True)
                    refresh.assert_not_called()
                p.unlink()
                for directory in [p.parent,self.out/'packets',self.out/'snapshot']:
                    if directory!=self.out and directory.is_dir() and not list(directory.iterdir()):directory.rmdir()
        self.assertEqual(self.rows(),[])
    def test_existing_frozen_resume_keeps_strict_input_check(self):
        self.fail_before_freeze()
        with self.assertRaises(StopAfterClaims):self.call(resume=True)
        with patch.object(context_batch,'check_inputs',side_effect=ContextError('frozen inputs changed')) as check,patch.object(self.operator,'ensure_fresh') as refresh:
            with self.assertRaisesRegex(ContextError,'frozen inputs changed'):self.call(resume=True)
            check.assert_called_once();refresh.assert_not_called()

if __name__=='__main__':unittest.main()
