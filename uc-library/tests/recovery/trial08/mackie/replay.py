"""Compare explicit portable executable outputs directly with ARM observations."""
import argparse,json,pathlib,subprocess
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixture-dir',required=True);a=p.parse_args();base=pathlib.Path(a.fixture_dir);count=0
for c in json.loads((base/'comparator-fixtures.json').read_text())['cases']:
 out=subprocess.check_output([a.executable,str(c['method']),str(c['a']),str(c['b'])],text=True);assert int(out)==c['result'],c;count+=1
for c in json.loads((base/'scrub-fixtures.json').read_text())['cases']:
 out=subprocess.check_output([a.executable,'10',str(c['direction'])],text=True);actual=[list(map(int,line.split())) for line in out.splitlines()];assert actual==c['midi'],c;count+=1
print('PASS',count,'native differential cases')
for c in json.loads((base/'lookup-fixtures.json').read_text())['cases']:
 args=[a.executable,str(c['method']),str(c['key'])]+[str(v) for row in c['entries'] for v in row];actual=int(subprocess.check_output(args,text=True));assert actual==c['index'],c;count+=1
for c in json.loads((base/'virtual-fixtures.json').read_text())['cases']:
 actual=json.loads(subprocess.check_output([a.executable,str(c['method']),str(c['arg']),str(c['state']),str(c['float_bits'])],text=True));expected={k:c[k] for k in ['trace','connection','assignment','timecode']};assert actual==expected,(c,actual);count+=1
for c in json.loads((base/'mapping-fixtures.json').read_text())['cases']:
 actual=json.loads(subprocess.check_output([a.executable,'3',str(c['initial_count']),str(c['tag']),str(c['note'])],text=True));assert actual==c['result'],c;count+=1
print('PASS complete',count,'native differential cases across ten targets')
