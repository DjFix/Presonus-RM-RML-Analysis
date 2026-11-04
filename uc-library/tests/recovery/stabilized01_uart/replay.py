import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--driver',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args();j=json.loads(Path(a.fixtures).read_text())
for c in j['cases']:
 r=subprocess.run([a.driver,c['scenario']],capture_output=True,text=True,check=True,timeout=10);actual=json.loads(r.stdout)
 # Actual CCL coredebug.cpp formats to a NUL-terminated buffer then calls DebugPrint.
 # Raw original DebugPrintf call arguments stay unchanged in the native fixture.
 expected=dict(c['native']['observed']);expected['messages']=[s.split('\0',1)[0] for s in expected['messages']]
 assert actual==expected,dict(task=c['task_id'],scenario=c['scenario'],actual=actual,expected=c['native']['observed'])
print('replayed',len(j['cases']),'helper/caller original observations; real UARTComm/CCL code with intercepted POSIX device/clock boundaries; no hardware access')
