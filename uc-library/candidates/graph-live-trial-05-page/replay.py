import argparse,json,pathlib,subprocess
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
d=json.loads(pathlib.Path(a.fixtures).read_text());cases=d['cases']
assert all(c['nonstack_writes']==[] for c in cases), 'Unexpected native side effects require expanded replay'
inputs=''.join(' '.join(str(c[k]) for k in ['n','owner','screen','current','editing','flag','ident'])+'\n' for c in cases)
r=subprocess.run([str(pathlib.Path(a.executable).resolve())],input=inputs,text=True,capture_output=True,check=True)
lines=r.stdout.splitlines();assert len(lines)==len(cases),(len(lines),len(cases),r.stderr)
for i,(c,line) in enumerate(zip(cases,lines)):
 actual=json.loads(line)
 expected={'result':c['result'] if c['n']!=4 else 0,'trace':c['trace']}
 assert actual==expected,(i,c,actual,expected)
print(json.dumps({'passed':True,'cases':len(cases),'scope':'five target ARM bodies versus portable C++ with instrumented external boundaries'}))
