import argparse,json,subprocess
from pathlib import Path
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'uc-library/tools/recovery/accept_worker.py').is_file())
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);a=p.parse_args()
lines=subprocess.check_output(['/usr/bin/nm','--defined-only',a.executable],text=True).splitlines();symbols={line.split()[-1] for line in lines if line.split()}
records=[]
for packet in sorted((ROOT/'temp/recovery-work/large02-lifecycle-fix01/batch03/packets').iterdir()):
 for target in json.loads((packet/'request.json').read_text())['targets']:
  assert target['mangled'] in symbols,target['mangled'];records.append(target['mangled'])
print(json.dumps(dict(passed=True,object_format='Linux ELF, no name decoration',originals=records,scope='Exact original case-sensitive mangling only; no layout/calling-convention/return/ARM ABI claim')))
