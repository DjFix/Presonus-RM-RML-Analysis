"""Compare a supplied compiled executable directly against original ARM captures."""
import argparse,json,subprocess,pathlib
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
f=json.loads(pathlib.Path(a.fixtures).read_text());failed=[]
for c in f['cases']:
 r=subprocess.run([str(pathlib.Path(a.executable).resolve()),str(c['method']),str(c['variant'])],text=True,capture_output=True)
 if r.returncode or r.stdout.strip()!=c['expected']:failed.append({'case':c,'actual':r.stdout.strip(),'returncode':r.returncode,'stderr':r.stderr})
if failed:print(json.dumps(failed,indent=2));raise SystemExit(1)
print(f"PASS {len(f['cases'])} differential cases; original instruction branches/stores plus explicit scripted application/provider boundaries")
