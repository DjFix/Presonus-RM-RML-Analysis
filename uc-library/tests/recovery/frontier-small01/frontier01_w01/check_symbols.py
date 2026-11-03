import pathlib,json,subprocess,argparse
p=argparse.ArgumentParser();p.add_argument('--object',required=True);a=p.parse_args()
root=pathlib.Path(__file__).resolve().parents[5]
out=subprocess.check_output(['nm','--defined-only',a.object],text=True);symbols={line.split()[-1] for line in out.splitlines() if line.split()}
for i in range(1,6):
 j=json.loads((root/f'temp/recovery-work/frontier-small01/batch01/packets/frontier01_w01_{i:02}/request.json').read_text())
 for t in j['targets']:assert t['mangled'] in symbols,t
print('Five exact original ELF mangled names in current Linux source object; no extra object-format decoration; names do not establish ARM ABI')
