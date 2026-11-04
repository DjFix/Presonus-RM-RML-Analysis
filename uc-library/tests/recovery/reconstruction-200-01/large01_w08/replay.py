import sys,json,subprocess,runpy
from pathlib import Path
if len(sys.argv)==1:
 sys.argv=['checks.py','replay'];runpy.run_path('uc-library/candidates/large01_w08/checks.py',run_name='__main__')
else:
 assert sys.argv[1]=='--executable' and len(sys.argv)==3
 rows=json.loads(Path(__file__).with_name('fixtures.json').read_text())
 from oracle import observe
 assert observe()==rows
 lines=subprocess.check_output([sys.argv[2]],text=True).splitlines();assert len(lines)==10
 for r,line in zip(rows,lines):
  if r['kind']=='audio':assert list(map(int,line.split()))==r['words']
  else:assert line.split('|')==[str(r['port']),*r['strings']]
 print('10 canonical portable cases match independently executed original ARM observations')
