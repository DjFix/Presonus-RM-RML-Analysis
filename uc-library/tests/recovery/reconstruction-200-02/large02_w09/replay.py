import argparse,json,subprocess
p=argparse.ArgumentParser();p.add_argument('--driver',required=True);p.add_argument('--fixture',required=True);a=p.parse_args();cases=json.load(open(a.fixture))['cases'];r=subprocess.run([a.driver],input='\n'.join(c['command'] for c in cases)+'\n',text=True,capture_output=True,check=True);lines=r.stdout.splitlines();assert len(lines)==len(cases),(len(lines),len(cases),r.stderr)
for c,line in zip(cases,lines):
 actual=list(map(float,line.split()));assert actual==c['expected'],(c,actual)
print(f'{len(cases)} optimized C++ observations match independent original ARM fixture')
