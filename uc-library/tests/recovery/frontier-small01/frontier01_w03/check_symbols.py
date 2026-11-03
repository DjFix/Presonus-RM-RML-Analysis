from pathlib import Path
import argparse,json,subprocess
p=argparse.ArgumentParser();p.add_argument('--object',required=True);a=p.parse_args()
actual=subprocess.check_output(['/usr/bin/nm','--defined-only',a.object],text=True)
names={x.split()[-1] for x in actual.splitlines() if x.split()}
for i in range(1,8):
 r=json.loads(Path(f'temp/recovery-work/frontier-small01/batch01/packets/frontier01_w03_{i:02d}/request.json').read_text())
 for t in r['targets']:
  assert t['mangled'] in names,t['mangled']
print('PASS 7 exact ELF mangled targets in Linux ELF object; distinct C1/C2 names retained; names do not establish original returns/layout/ARM ABI')
