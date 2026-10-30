"""Replay exact original control/lifecycle inputs; all effects intercepted."""
import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser()
for name in ('binary','stdin','fixture'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();rows=[json.loads(s) for s in a.fixture.read_text().splitlines()];assert len(rows)==822
lines=[]
for row in rows:
 c=row['input'];lines.append(' '.join(map(str,[c['kind'],int(c['lazy']),c['serial'],c['unit'],c['ack'],c['status'],*c['ticks'],c['info_result'],*c['seed'],c['command'],c['initial_status'],c['response_word']])))
stdin='\n'.join(lines)+'\n';assert a.stdin.read_text()==stdin
r=subprocess.run([str(a.binary)],input=stdin,text=True,capture_output=True);assert r.returncode==0,r.stderr
actual=[]
for line in r.stdout.splitlines():
 if line.startswith('{'):actual.append(json.loads(line))
 else:assert line=='UART: close port -1',line
assert len(actual)==len(rows)
for row,value in zip(rows,actual):assert row['expected']==value,(row['index'],row['expected'],value)
assert 'actual variant calls C1=32 C2=32' in r.stderr,r.stderr
print('PASS 822 original control/lifecycle traces, real variants and CCL registry; all device effects intercepted')
