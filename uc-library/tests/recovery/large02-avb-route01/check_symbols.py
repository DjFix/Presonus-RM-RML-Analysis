import argparse,subprocess,json
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);a=p.parse_args()
name='_ZN8Presonus5Mixer18MixerComponentBase16routeInputsToNetEv'
rows=subprocess.check_output(['/usr/bin/nm','--defined-only',a.executable],text=True).splitlines()
assert any(r.split()[-1]==name for r in rows)
print(json.dumps({'mangled':name,'matched':True,'scope':'Linux ELF name only; return declaration/layout/ARM ABI unresolved'}))
