"""Compare canonical C++ executable observations to independent ARM fixtures."""
import json,subprocess,sys
from pathlib import Path
fixture=Path(sys.argv[2]);data=json.loads(fixture.read_text());lines=[]
for case in data['cases']:
 c=case['input'];lines.append(' '.join(map(str,[c['mode'],len(c['values']),c['arg'],c['selected'],c['sentinel']]+c['values'])))
p=subprocess.run([sys.argv[1]],input='\n'.join(lines)+'\n',text=True,capture_output=True,check=True)
actual=p.stdout.splitlines();assert len(actual)==len(lines),(len(actual),len(lines),p.stderr)
for i,(line,case) in enumerate(zip(actual,data['cases'])):
 assert list(map(int,line.split()))==case['expected'],(i,case['input'],line,case['expected'])
print('PASS',len(lines),'C++ executions against original ARM observations; counts, retained storage, return values')
