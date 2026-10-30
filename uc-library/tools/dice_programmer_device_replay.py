"""Replay retained offline GPIO/SPI/fd lifetime traces with exact input binding."""
import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--binary',type=Path,required=True);p.add_argument('--stdin',type=Path,required=True);p.add_argument('--fixture',type=Path,required=True);a=p.parse_args()
rows=list(map(json.loads,a.fixture.read_text().splitlines()));assert len(rows)==1280;lines=[]
for row in rows:
 c=row['input'];lines.append(' '.join(map(str,[0 if c['kind']=='open' else 1,c['initial_fd'],c['opened_fd'],c['read_result'],c['write_result'],c['mode'],c['jedec'],c['jedec_result'],c['manufacturer'],c['close_result'],c['stdio_result'],int(c['put_error']),c['errno'],c['path'].encode().hex() or '-'])))
stdin='\n'.join(lines)+'\n';assert a.stdin.read_text()==stdin;r=subprocess.run([str(a.binary)],input=stdin,text=True,capture_output=True);assert r.returncode==0,r.stderr
actual=list(map(json.loads,r.stdout.splitlines()));assert len(actual)==len(rows)
for row,value in zip(rows,actual):assert row['expected']==value,(row['index'],row['expected'],value)
print('PASS 1280 original open/close GPIO/fd/SPI traces; all physical effects intercepted')
