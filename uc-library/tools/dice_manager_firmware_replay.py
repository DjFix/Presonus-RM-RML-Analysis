"""Replay retained manager firmware traces; no physical operations."""
import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser()
for name in ('binary','stdin','fixture'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();rows=[json.loads(s) for s in a.fixture.read_text().splitlines()]
assert len(rows)==260
stdin=''.join(' '.join(map(str,[r['input']['kind'],r['input']['open'],r['input']['result'],r['input']['length'],int(r['input']['listener'])]))+'\n' for r in rows)
assert a.stdin.read_text()==stdin
r=subprocess.run([str(a.binary)],input=stdin,text=True,capture_output=True)
assert r.returncode==0,r.stderr
actual=[json.loads(s) for s in r.stdout.splitlines()]
assert len(actual)==len(rows)
for row,value in zip(rows,actual):assert row['expected']==value,(row['index'],row['expected'],value)
print('PASS 260 original manager firmware traces; programmer boundaries intercepted')
