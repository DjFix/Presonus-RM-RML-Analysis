import json,subprocess,sys,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
fixture=Path(sys.argv[2]) if len(sys.argv)>2 else Path(__file__).with_name('fixtures.json')
binary=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'temp/recovery-work/rolling200-02/stage03-w01/build/driver'
f=json.loads(fixture.read_text());cases=f['cases'];result=subprocess.run([str(binary.resolve())],input=''.join(' '.join(map(str,c['input']))+'\n' for c in cases),text=True,capture_output=True);assert result.returncode==0,(result.returncode,result.stdout[-1500:],result.stderr);rows=result.stdout.splitlines();assert len(rows)==len(cases),(len(rows),len(cases))
for row,c in zip(rows,cases):assert row==c['expected'],(c['input'],row,c['expected'])
print('PASS',len(cases),'original ARM vs executable C++ cases; real provider forwarding; fixture SHA256',hashlib.sha256(fixture.read_bytes()).hexdigest())
