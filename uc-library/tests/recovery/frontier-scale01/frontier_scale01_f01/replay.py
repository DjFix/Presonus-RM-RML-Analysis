import json,subprocess,sys
from pathlib import Path
fixture=Path(sys.argv[2]) if len(sys.argv)>2 else Path(__file__).with_name('fixtures.json')
data=json.loads(fixture.read_text()); count=0
for case in data['cases']:
 got=list(map(int,subprocess.check_output([sys.argv[1],str(case['argument_bits'])],text=True).split()))
 assert got==case['expected']+[1,1]+[0]*7,(case,got)
 count+=1
print(f'PASS {count} per-original constructor projections; borrowed adapter mutation/null/bounds regression; independent copy storage')
