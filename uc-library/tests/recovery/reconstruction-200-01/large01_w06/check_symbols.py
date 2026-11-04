import subprocess,sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]
names=set(line.split()[-1] for line in subprocess.check_output(['nm','--defined-only',sys.argv[1]],text=True).splitlines() if line.split())
for i in range(1,11):
 d=json.loads((ROOT/f'temp/recovery-work/reconstruction-200-01/large-batch01/packets/large01_w06_{i:02}/request.json').read_text())
 for t in d['targets']:
  assert t['mangled'] in names,t['mangled']
  print(t['mangled'])
print('PASS all 10 exact original Linux C++ symbol identities')
