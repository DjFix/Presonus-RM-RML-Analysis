import argparse,subprocess,pathlib,json,datetime,time,hashlib,os
B=pathlib.Path('uc-library/candidates/graph-live-trial-05-page');S=pathlib.Path('temp/recovery-work/graph-live-trial-05/page-worker');S.mkdir(parents=True,exist_ok=True)
p=argparse.ArgumentParser();p.add_argument('phase',choices=['format','compile','symbols','replay']);a=p.parse_args()
paths=['uc-library/include/presonus/PageComponent.hpp','uc-library/src/Presonus/PageComponent.cpp','uc-library/tests/graph_trial05_page_tests.cpp']
cmds={'format':[['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*paths]],'compile':[['c++','-std=c++17','-Wall','-Wextra','-Werror','-Iuc-library/include','uc-library/src/Presonus/PageComponent.cpp','uc-library/tests/graph_trial05_page_tests.cpp','-o',str(S/'page-tests')]],'symbols':[['nm','--defined-only',str(S/'page-tests')]],'replay':[['uc-library/.venv/bin/python',str(B/'replay.py'),'--executable',str(S/'page-tests'),'--fixtures',str(B/'fixtures.json')]]}
start=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic(); logs=[]
for cmd in cmds[a.phase]:
 r=subprocess.run(cmd,text=True,capture_output=True);logs.append(dict(argv=cmd,exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0,logs
 if a.phase=='symbols':
  d=json.loads((B/'fixtures.json').read_text());
  for x in d['ranges']:assert x['mangled'] in r.stdout,x
out=dict(phase=a.phase,start=start,end=datetime.datetime.now(datetime.timezone.utc).isoformat(),duration_seconds=time.monotonic()-t,commands=logs,session_id=os.environ.get('CODEX_THREAD_ID'))
(S/(a.phase+'.json')).write_text(json.dumps(out,indent=2)+'\n');print(a.phase,'passed')
