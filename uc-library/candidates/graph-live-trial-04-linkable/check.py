"""Read-only checks of sealed inputs; compilation only writes worker scratch."""
import pathlib,subprocess,sys,json,hashlib,datetime,time
B=pathlib.Path('uc-library/candidates/graph-live-trial-04-linkable');S=pathlib.Path('temp/recovery-work/graph-live-trial-04/linkable-worker');S.mkdir(parents=True,exist_ok=True)
paths=['uc-library/include/presonus/LinkableComponent.hpp','uc-library/src/Presonus/LinkableComponent.cpp','uc-library/tests/graph_trial04_linkable_tests.cpp']
exe=str(S/'replay');mode=sys.argv[1]
commands={'format':['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*paths], 'compile':['g++','-std=c++17','-Wall','-Wextra','-Werror','-Iuc-library/include',paths[1],paths[2],'-o',exe], 'symbols':['nm','--defined-only',exe], 'replay':[exe,str(B/'fixtures.txt')]}
if mode=='replay' and len(sys.argv)>2:commands['replay']=[sys.argv[2],str(B/'fixtures.txt')]
start=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic();r=subprocess.run(commands[mode],capture_output=True,text=True)
if mode=='symbols':
 names={line.split()[-1] for line in r.stdout.splitlines() if line.split()}
 expected=[json.loads(pathlib.Path(f'temp/recovery-work/graph-live-trial-04/trial04_linkable_{i}-packet/context.json').read_text())['originals'][0]['original']['mangled'] for i in range(1,6)]
 assert all(x in names for x in expected)
 print('\n'.join(expected))
else:print(r.stdout,r.stderr,end='')
log={'start_utc':start,'end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'seconds':time.monotonic()-t,'argv':commands[mode],'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
(S/f'{mode}-last.json').write_text(json.dumps(log,indent=2)+'\n')
sys.exit(r.returncode)
