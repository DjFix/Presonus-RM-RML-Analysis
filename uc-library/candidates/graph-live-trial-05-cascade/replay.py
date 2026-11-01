import argparse,json,subprocess
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
f=json.load(open(a.fixtures))
for i,c in enumerate(f['cases']):
 r=subprocess.run([a.executable,*c['argv']],capture_output=True,text=True,check=True)
 assert r.stdout.splitlines()==c['observed'],(i,c,r.stdout)
print('passed',len(f['cases']),'original ARM boundary differential cases')
