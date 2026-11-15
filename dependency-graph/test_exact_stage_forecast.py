import pathlib,sys,sqlite3,tempfile,unittest
R=pathlib.Path(__file__).resolve().parents[1];D=R/'temp';sys.path.insert(0,str(R/'dependency-graph'))
from compact_facts import create_schema
from incremental_stage import IncrementalStage
from incremental_delta import NetChanges
from batch_publication import request_forecast,journal_preflight
from publication_budget import PublicationBudget,BudgetLimits,BudgetExceeded
from deferred_sqlite import deferred_reserve

class Forecast(unittest.TestCase):
 def stage(self, transfer=64*1024**2):
  c=sqlite3.connect(':memory:');create_schema(c);c.commit();c.execute('BEGIN');delta=sqlite3.connect(':memory:');delta.execute('BEGIN');budget=PublicationBudget(BudgetLimits(transfer_bytes=transfer));stage=IncrementalStage(c,budget);return c,delta,budget,stage
 def test_same_uncommitted_journal_exact_forecast_seal_and_no_double_rows(self):
  c,d,b,s=self.stage();s.replace_facts('owner',{'a':{'kind':'file','label':'α','metadata':{'path':'α.cpp','text':'界'*100}}},set());s.finish(d)
  self.assertIsNone(d.row_factory);d.row_factory=sqlite3.Row;actual=request_forecast(d)
  self.assertEqual(s.totals['transfer_estimate_bytes'],actual['json_request_estimate_bytes']);self.assertEqual(b.estimates['transfer_bytes'],actual['json_request_estimate_bytes']);self.assertEqual(b.rows,s.actual_storage_rows+s.actual_delta_rows+s.actual_prune_rows)
  self.assertEqual(b.completed_stage_estimate['estimates'],b.estimates);self.assertGreater(b.estimates['sqlite_write_bytes'],0);self.assertTrue(c.in_transaction and d.in_transaction);c.rollback();d.rollback();c.close();d.close()
 def test_exact_guard_before_finish_seal_or_commit(self):
  c,d,b,s=self.stage(500);s.replace_facts('owner',{},set())
  with self.assertRaises(BudgetExceeded):s.finish(d)
  self.assertFalse(hasattr(b,'completed_stage_estimate'));self.assertTrue(c.in_transaction and d.in_transaction);c.rollback();d.rollback();c.close();d.close()
 def test_same_shapes_as_disk_journal_preflight_and_fixed_digest_length(self):
  with tempfile.TemporaryDirectory(dir=D) as tmp:
   p=pathlib.Path(tmp)/'delta.sqlite';d=sqlite3.connect(p);d.row_factory=sqlite3.Row;net=NetChanges();net.nodes={'a':(None,dict(id='a',kind='file',label='界',metadata='{}'))};net.edges={('a','b','USES','provenance'):(False,True)};net.write(d);d.commit();a=request_forecast(d);budget=PublicationBudget();b=journal_preflight(d,p,budget,1000);self.assertEqual(a['json_request_estimate_bytes'],b['json_request_estimate_bytes']);self.assertEqual(a['planned_json_requests'],b['planned_json_requests']);d.close()
 def test_reserve_max_total_estimate_not_additive_checkpoint(self):
  c=sqlite3.connect(':memory:');d=sqlite3.connect(':memory:');b=PublicationBudget();b.preflight(journal_estimate_bytes=0,sqlite_write_estimate_bytes=100*1024**2,rows=0,transfer_bytes=0);b.completed_stage_estimate=dict(complete=True,estimates=dict(b.estimates));b.write_bytes=20*1024**2
  # Memory journal is intentionally unsupported; real path fixture for reserve.
  c.close();d.close()
  with tempfile.TemporaryDirectory(dir=D) as tmp:
   paths=[pathlib.Path(tmp)/'main.sqlite',pathlib.Path(tmp)/'delta.sqlite'];cs=[sqlite3.connect(p) for p in paths];r=deferred_reserve(cs,paths,b);self.assertEqual(b.write_bytes+r['bytes'],104*1024**2)
   for connection in cs:connection.close()

if __name__=='__main__':unittest.main()
