import pathlib,sys,sqlite3,tempfile,json,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
from incremental_delta import NetChanges
from incremental_stage import delta_reserve

def io():return int(dict(line.split(':',1) for line in pathlib.Path('/proc/self/io').read_text().splitlines())['write_bytes'])
MEASUREMENTS=[]
class FreshDelta(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=ROOT/'temp/test-work',prefix='fresh-delta-cost-');self.addCleanup(self.temp.cleanup);self.path=pathlib.Path(self.temp.name)/'delta.sqlite'
 def db(self):return sqlite3.connect(self.path)
 def fixture(self,count,identity_chars,metadata_chars,edges):
  net=NetChanges()
  for i in range(count):
   key=('f:'+str(i)+':'+('λ'*(identity_chars//2)))
   after=dict(id=key,kind='Function',label='label'+str(i),metadata=json.dumps({'text':'x'*metadata_chars,'i':i}))
   net.nodes[key]=(None,after)
  keys=list(net.nodes)
  for i in range(edges):net.edges[(keys[i%count],keys[(i+1)%count],'CALLS',json.dumps({'tu':i//100,'event':i}))]=(False,True)
  return net
 def measured(self,shape):
  net=self.fixture(*shape);before=io();c=self.db();c.execute('BEGIN');plan=net.plan();reserve=delta_reserve(c,net.nodes,plan);self.assertEqual(reserve['storage_case'],'fresh_empty_delete' if shape[1]<=768 else 'conservative_old_state');self.assertEqual(reserve['additional_primary_key_index_bytes'],sum(len(k.encode()) for k in net.nodes) if shape[1]<=768 else 0);net.write(c);c.commit();c.close();writes=io()-before;size=self.path.stat().st_size
  self.assertLessEqual(size,reserve['journal_estimate_bytes']);self.assertLessEqual(writes,reserve['sqlite_write_estimate_bytes']);MEASUREMENTS.append(dict(shape=shape,plan=plan,reserve=reserve,actual_database_bytes=size,actual_process_write_bytes=writes))
 def test_small_mixed_rows_measured(self):self.measured((100,64,100,400))
 def test_large_metadata_measured(self):self.measured((300,64,16384,900))
 def test_long_unicode_ids_primary_index_measured(self):self.measured((100,16384,10,300))
 def test_cache_pressure_measured(self):self.measured((5000,200,1500,20000))
 def test_existing_schema_keeps_old_cost(self):
  c=self.db();c.execute('CREATE TABLE existing(x)');c.commit();c.execute('BEGIN');p=dict(payload_bytes=1000,rows=10);r=delta_reserve(c,['x'],p);self.assertEqual(r['storage_case'],'conservative_old_state');self.assertEqual(r['journal_estimate_bytes'],32768+2000+1280);c.close()
 def test_wal_keeps_old_cost(self):
  c=self.db();c.execute('PRAGMA journal_mode=WAL');c.execute('BEGIN');self.assertEqual(delta_reserve(c,[],dict(payload_bytes=0,rows=1))['storage_case'],'conservative_old_state');c.close()
 def test_memory_keeps_old_cost(self):
  c=sqlite3.connect(':memory:');c.execute('BEGIN');self.assertEqual(delta_reserve(c,[],dict(payload_bytes=0,rows=1))['storage_case'],'conservative_old_state');c.close()
 def test_nondefault_pages_keep_old_cost(self):
  c=self.db();c.execute('PRAGMA page_size=512');c.execute('BEGIN');self.assertEqual(delta_reserve(c,[],dict(payload_bytes=0,rows=1))['storage_case'],'conservative_old_state');c.close()
if __name__ == '__main__':
 unittest.main()
