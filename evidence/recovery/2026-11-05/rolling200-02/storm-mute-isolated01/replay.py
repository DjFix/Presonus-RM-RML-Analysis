import argparse,json,subprocess
p=argparse.ArgumentParser();p.add_argument('--exe',required=True);p.add_argument('--fixture',required=True);a=p.parse_args()
cases=json.load(open(a.fixture))['cases']
for c in cases:
 r=subprocess.run([a.exe,'mute',str(c['index']),'<null>' if c['prefix'] is None else c['prefix']],capture_output=True,text=True,check=True)
 assert r.stdout==c['native_output'],(c,r.stdout)
print('PASS',len(cases),'native fixture cases, mute createDefaultName')
