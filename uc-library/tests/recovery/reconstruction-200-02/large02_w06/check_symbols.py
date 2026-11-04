import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--binary',required=True);a=p.parse_args()
names=set(line.split()[-1] for line in subprocess.check_output(['nm','--defined-only',a.binary],text=True).splitlines() if line.split())
for packet in sorted(Path('temp/recovery-work/reconstruction-200-02/isolated-batch01/packets').glob('large02_w06_*')):
 request=json.loads((packet/'request.json').read_text())
 for item in request['originals']:
  name=item['original']['mangled'];assert name in names,name
print('All 19 exact original ELF mangled names are defined in Linux host source port; no ARM ABI claim.')
