import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--binary',required=True);a=p.parse_args();symbols={x.split()[-1]for x in subprocess.check_output(['nm','--defined-only',a.binary],text=True).splitlines()if x.split()};names=[]
for i in range(1,17):
 j=json.loads(Path(f'temp/recovery-work/reconstruction-200-02/isolated-batch01/packets/large02_w04_{i:02}/request.json').read_text());names +=[x['mangled']for x in j['targets']]
missing=set(names)-symbols
assert not missing,missing
print('exact ELF mangling names',len(names),'host ELF no decoration; portable source not original ARM ABI')
