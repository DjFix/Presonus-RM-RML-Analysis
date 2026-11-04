import json,subprocess,sys
f=json.load(open(sys.argv[2])); cases=f['cases']
p=subprocess.run([sys.argv[1]],input=''.join(' '.join(map(str,c['input']))+'\n' for c in cases),text=True,capture_output=True,check=True)
actual=[list(map(int,l.split())) for l in p.stdout.splitlines()]
assert actual==[c['output'] for c in cases],(actual,p.stderr)
print('passed',len(cases),'native call-trace/provider cases')
