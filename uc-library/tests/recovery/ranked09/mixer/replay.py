import json, subprocess, sys
from pathlib import Path
fixture=json.loads(Path(sys.argv[2]).read_text())
cases=fixture['cases']
data=''.join('delegate '+' '.join(map(str,[len(c['items']),c['target'],c['sentinel'],*c['items']]))+'\n' for c in cases)
r=subprocess.run([sys.argv[1]],input=data,text=True,capture_output=True,check=True)
lines=r.stdout.splitlines()
assert len(lines)==len(cases)
for i,(c,line) in enumerate(zip(cases,lines)):
    assert list(map(int,line.split()))==[c['count'],*c['backing']],(i,c,line)
print(f'{len(cases)} original ARM / portable CCL-backed delegate removal cases passed')

solo=fixture.get('solo_cases',[])
if solo:
    data=''.join('solo '+' '.join(map(str,[*c['coefficients'],*c['cached_before'],c['count_before']]))+'\n' for c in solo)
    r=subprocess.run([sys.argv[1]],input=data,text=True,capture_output=True,check=True)
    lines=r.stdout.splitlines(); assert len(lines)==len(solo)
    for i,(c,line) in enumerate(zip(solo,lines)):
        expected=[c['count'],*c['cached'],*[v for e in c['entries'] for v in e]]
        assert list(map(int,line.split()))==expected,(i,c,line)
    print(f'{len(solo)} original ARM / opaque-adapter soloUpdate cases passed')

pairs=fixture.get('pair_cases',[])
if pairs:
    data=''.join('pair '+' '.join(map(str,[c['type'],c['index'],c['inputs'],c['mixes'],c['sentinel']]))+'\n' for c in pairs)
    r=subprocess.run([sys.argv[1]],input=data,text=True,capture_output=True,check=True)
    lines=r.stdout.splitlines(); assert len(lines)==len(pairs)
    for i,(c,line) in enumerate(zip(pairs,lines)):
        assert list(map(int,line.split()))==[c['result'],1],(i,c,line)
    r=subprocess.run([sys.argv[1]],input='missing\n',text=True,capture_output=True,check=True)
    assert r.stdout=='missing-binding-threw\n'
    print(f'{len(pairs)} original ARM / required-query pair cases passed; missing binding throws')
