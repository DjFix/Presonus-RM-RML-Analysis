import json,subprocess,sys
from pathlib import Path
fixtures=Path(sys.argv[2]) if len(sys.argv)>2 else Path(__file__).with_name('fixtures.json')
cases=json.loads(fixtures.read_text())['cases']
inputs=''.join(f"{c['kind']} {c['count']} {c['query']} {c['records'] or '-'}\n" for c in cases)
r=subprocess.run([sys.argv[1]],input=inputs,text=True,capture_output=True,check=True)
lines=r.stdout.splitlines();assert len(lines)==len(cases)
for c,line in zip(cases,lines):
 index,payload,unchanged=line.split();assert (int(index),payload,unchanged)==(c['index'],c['payload'] or '-','1'),(c,line)
print(f'{len(cases)} original ARM/C++ cases match; records unchanged; no original nonstack writes')
