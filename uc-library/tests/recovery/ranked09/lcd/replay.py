import argparse,json,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[5]
p=argparse.ArgumentParser();p.add_argument('--exe',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
f=json.loads(Path(a.fixtures).read_text())
for case in f['cases']:
 result=[int(x) for x in subprocess.check_output([a.exe,str(case['target']),str(case['count']),str(case['arg'])],text=True).split()]
 obs=case['observed'];assert result==[obs['count'],obs['result'],*obs['items']],(case,result)
print(f"{len(f['cases'])} portable C++/real CCL stack replays match original ARM results, count, all active/inactive slots")
