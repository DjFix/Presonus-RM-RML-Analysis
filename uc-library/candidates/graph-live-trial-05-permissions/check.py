#!/usr/bin/env python3
import argparse, subprocess, pathlib, json, hashlib, datetime, time, os
P=pathlib.Path('uc-library/candidates/graph-live-trial-05-permissions')
W=pathlib.Path('temp/recovery-work/graph-live-trial-05/permissions-worker')
S=['uc-library/src/Presonus/Mixer/PermissionsComponent.cpp','uc-library/include/presonus/mixer/PermissionsComponent.hpp','uc-library/tests/graph_trial05_permissions_tests.cpp']
p=argparse.ArgumentParser();p.add_argument('kind',choices=['format','compile','symbols','replay']);p.add_argument('--executable',default=str(W/'test'));p.add_argument('--fixtures',default=str(P/'native-fixtures.json'));a=p.parse_args()
os.environ['TMPDIR']=str(W.resolve())
start=time.monotonic();commands=[]
def run(cmd):
 commands.append(cmd);r=subprocess.run(cmd,text=True,capture_output=True);log=W/(a.kind+'-commands.jsonl');log.open('a').write(json.dumps({'argv':cmd,'stdout':r.stdout,'stderr':r.stderr,'returncode':r.returncode,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})+'\n');r.check_returncode();return r.stdout
if a.kind=='format':
 run(['uc-library/.venv/bin/clang-format','--version']);run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*S])
elif a.kind=='compile':
 args=['/usr/bin/c++','-std=c++17','-O2','-fno-lto','-UNDEBUG','-fno-rtti','-pthread','-Ulinux','-Iuc-library/include','-Itemp/core-upstream/root-integration-01/upstream-core/sdk/include/presonus-core-5']
 run([*args,'-c',S[0],'-o',str(W/'permissions.o')]);run([*args,S[2],str(W/'permissions.o'),'temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a','-lpthread','-ldl','-lm','-o',a.executable])
elif a.kind=='symbols':
 text=run(['/usr/bin/nm','--defined-only',str(W/'permissions.o')]);symbols={line.split()[-1] for line in text.splitlines() if line.split()}
 fixtures=json.loads(pathlib.Path(a.fixtures).read_text())
 for o in fixtures['ranges']:assert o['mangled'] in symbols,o['mangled']
else:
 fixtures=json.loads(pathlib.Path(a.fixtures).read_text())
 for c in fixtures['cases']:
  x=c['input']; cmd=[a.executable,str(c['target']),str(int(x.get('selected',False))),x.get('name','client'),x.get('payload',''),str(int(x.get('enabled',False))),str(x.get('restricted',0)),str(x.get('dirty',0))]
  out=json.loads(run(cmd));assert out==c['observed'],(c['case_id'],out,c['observed'])
 print('Differential replay passed',len(fixtures['cases']),'cases against explicit executable',a.executable)
record={'kind':a.kind,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'duration_seconds':time.monotonic()-start,'commands':commands,'outcome':'passed'}
(W/(a.kind+'-check.json')).write_text(json.dumps(record,indent=2)+'\n')
