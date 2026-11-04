import json,subprocess,sys
from pathlib import Path
import oracle
cases=json.loads(Path(__file__).with_name('fixtures.json').read_text())
assert oracle.fixtures()==cases
for c in cases:
 argv=[sys.argv[1],str(c['index']),str(c['input'] or 0)]
 if c['input'] is None:argv.append('null')
 got=subprocess.check_output(argv,text=True)
 expected=1 if c['index'] in (2,3,5) else c['result']
 assert got==str(expected),(c,got,expected)
 if c['index'] in (2,3,5):assert c['calls']==[0x11b5e0]
print('PASS',len(cases),'native cases and portable/provider observations')
