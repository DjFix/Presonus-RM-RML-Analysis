"""Integration regression on a dedicated empty Memgraph, never the production endpoint."""
import json,pathlib,sqlite3,sys
from neo4j import GraphDatabase
from batch_publication import publish
from context_runtime import ContextError

out=pathlib.Path(sys.argv[1]);uri=sys.argv[2]
assert 'batch-test' in uri
out.mkdir(parents=True,exist_ok=True)
db=out/'delta.sqlite';c=sqlite3.connect(db);c.row_factory=sqlite3.Row
c.executescript('''CREATE TABLE settings(key,value);INSERT INTO settings VALUES('replace_legacy_build',0);
CREATE TABLE nodes(id,kind,label,metadata);CREATE TABLE old_edges(src,dst,kind,evidence);
CREATE TABLE new_edges(src,dst,kind,evidence);CREATE TABLE orphan_nodes(id);''')
c.executemany('INSERT INTO nodes VALUES(?,?,?,?)',[(x,'Function',x,'{}') for x in ('a','b','c')])
c.executemany('INSERT INTO new_edges VALUES(?,?,?,?)',[('a','b','CALLS','site'),('b','c','USES_DATA','site')]);c.commit()
with GraphDatabase.driver(uri,auth=None) as driver:
 with driver.session() as s:
  s.run('CREATE(:ContextGeneration {id:"active",state:"ready",digest:"test"})').consume()
  try:publish(s,c,db,out/'commits.jsonl',batch_size=1,stop_after=2)
  except ContextError as e:assert 'Injected interruption' in str(e)
  else:raise AssertionError('Expected interruption')
  checkpoint=dict(s.run('MATCH(p:PublicationCheckpoint) RETURN p.phase AS phase,p.last_row AS last_row,p.commits AS commits').single())
  assert checkpoint=={'phase':0,'last_row':2,'commits':2}
  assert s.run('MATCH(g:ContextGeneration) RETURN g.state AS state').single()['state']=='refreshing'
  before=s.run('MATCH(n:Artifact) RETURN count(n) AS n').single()['n'];assert before==2
  receipt=publish(s,c,db,out/'commits.jsonl',batch_size=1)
  assert s.run('MATCH(n:Artifact) RETURN count(n) AS n').single()['n']==3
  assert s.run('MATCH(:Artifact)-[r]->(:Artifact) RETURN count(r) AS n').single()['n']==2
  nlines=len((out/'commits.jsonl').read_text().splitlines())
  publish(s,c,db,out/'commits.jsonl',batch_size=1)
  assert len((out/'commits.jsonl').read_text().splitlines())==nlines
  # A failed edge batch must not commit its checkpoint, and a caller must not
  # mark the partial generation ready.
  bad=out/'bad.sqlite';b=sqlite3.connect(bad);b.row_factory=sqlite3.Row;c.backup(b)
  b.execute('DELETE FROM new_edges');b.execute('INSERT INTO new_edges VALUES(?,?,?,?)',('a','missing','CALLS','bad'));b.commit()
  try:publish(s,b,bad,out/'bad-commits.jsonl',batch_size=1)
  except ContextError as e:assert 'Missing/duplicate' in str(e)
  else:raise AssertionError('Expected missing endpoint rejection')
  badcp=dict(s.run('MATCH(p:PublicationCheckpoint {id:$id}) RETURN p.phase AS phase,p.last_row AS last_row',id='source-delta:'+__import__('hashlib').file_digest(bad.open('rb'),'sha256').hexdigest()).single())
  assert badcp=={'phase':2,'last_row':0}
  assert s.run('MATCH(g:ContextGeneration) RETURN g.state AS state').single()['state']=='refreshing'
  result={'passed':True,'injected_interruption_checkpoint':checkpoint,'resume_skips_committed_batches':True,'second_resume_no_writes':True,'missing_endpoint_rolls_back_checkpoint':True,'final_node_count':3,'final_edge_count':2,'publication':receipt}
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
