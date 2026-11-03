import argparse,json,pathlib,subprocess
p=argparse.ArgumentParser();p.add_argument('--object',required=True);a=p.parse_args()
root=pathlib.Path(__file__).resolve().parents[5]
names=set(line.split()[-1] for line in subprocess.check_output(['nm','--defined-only',a.object],text=True).splitlines() if line.split())
required=[]
for n in range(1,5):
 j=json.loads((root/f'temp/recovery-work/frontier-small01/batch01/packets/frontier01_w02_{n:02}/request.json').read_text())
 required.extend(t['mangled'] for t in j['targets'])
assert set(required)<=names,sorted(set(required)-names)
print(json.dumps({'required_original_symbols':required,'matched':len(required),'object_format':'Linux ELF; no Mach-O underscore decoration','scope':'exact encoded names only; unencoded returns/layout/ARM ABI remain unresolved'}))
