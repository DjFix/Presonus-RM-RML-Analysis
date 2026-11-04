import argparse,subprocess,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);a=p.parse_args();names=set()
for line in subprocess.check_output(['nm','--defined-only',a.executable],text=True).splitlines():
 if line.split():names.add(line.split()[-1])
expected=[]
for packet in sorted(Path('temp/recovery-work/reconstruction-200-02/isolated-batch01/packets').glob('large02_w05_*')):
 if packet.name=='large02_w05_05':continue
 expected += [x['mangled'] for x in json.loads((packet/'request.json').read_text())['targets']]
assert all(x in names for x in expected),set(expected)-names
print(json.dumps({'matched':expected,'format':'ELF Linux x86-64, no decoration; portable names only, not ARM ABI'}))
