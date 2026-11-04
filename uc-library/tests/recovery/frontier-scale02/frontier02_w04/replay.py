import json,subprocess,sys
from pathlib import Path
fixture=json.loads(Path(sys.argv[2]).read_text())
inputs=''.join(' '.join(map(str,c['input']))+'\n' for c in fixture['cases'])
p=subprocess.run([sys.argv[1]],input=inputs,text=True,capture_output=True,check=True)
actual=[list(map(int,line.split())) for line in p.stdout.splitlines()]
expected=[c['portable_observation'] for c in fixture['cases']]+[fixture['integration']['portable_observation']]
assert actual==expected,(actual,expected)
print('constructor native/provider replay cases',len(actual),'plus inherited-control and real ioctl-provider interception')
