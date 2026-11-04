"""Verify original ELF mangled identities in current compiled ELF symbols."""
import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);a=p.parse_args()
root=next(p for p in Path(__file__).resolve().parents if (p/'uc-library/tools/recovery/accept_worker.py').is_file())
names=set(line.split()[-1] for line in subprocess.check_output(['nm','--defined-only',a.executable],text=True).splitlines() if line.split())
checked=[]
for i in [1,5,7,8,9,10,11,12,15,16,17,18,19,20]:
 r=json.loads((root/f'temp/recovery-work/reconstruction-200-02/isolated-batch01/packets/large02_w01_{i:02}/request.json').read_text())
 for target in r['targets']:
  if target['mangled'] not in names:raise RuntimeError('Missing original identity: '+target['mangled'])
  checked.append(target['mangled'])
print(json.dumps({'passed':True,'checked':checked,'format':'Linux ELF; no leading decoration; source signature identity only; ordinary returns/ARM ABI unresolved'}))
