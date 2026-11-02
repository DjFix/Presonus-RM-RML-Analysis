import argparse,json,pathlib,subprocess
p=argparse.ArgumentParser();p.add_argument('--object',required=True);p.add_argument('--originals',required=True);a=p.parse_args()
names={line.split()[-1] for line in subprocess.check_output(['/usr/bin/nm','--defined-only',a.object],text=True).splitlines() if line.split()}
originals=json.loads(pathlib.Path(a.originals).read_text());missing=[x['mangled'] for x in originals if x['mangled'] not in names]
assert not missing,missing
print(len(originals),'exact original mangled names found in Linux ELF object; returns/layout/ABI unresolved')
