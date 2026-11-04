"""Local compile/symbol checks; outputs confined to owned project scratch."""
import os,pathlib,subprocess,sys,json
ROOT=pathlib.Path(__file__).resolve().parents[5];os.chdir(ROOT)
scratch=ROOT/'temp/recovery-work/graph-live-trial-08/mackie-worker';scratch.mkdir(parents=True,exist_ok=True)
exe=str(scratch/'replay')
if sys.argv[1]=='compile':
 env=dict(os.environ,TMPDIR=str(scratch));subprocess.run(['g++','-std=c++17','-Iuc-library/include','uc-library/src/Presonus/MackieControlModel.cpp','uc-library/tests/graph_trial08_mackie_tests.cpp','-o',exe],check=True,env=env)
elif sys.argv[1]=='symbols':
 output=subprocess.check_output(['nm','--defined-only',exe],text=True);names={line.split()[-1] for line in output.splitlines() if line.split()}
 for i in range(1,11):
  ctx=json.loads((ROOT/f'temp/recovery-work/graph-live-trial-08/batch03/packets/trial08_mackie_{i}/native-context.json').read_text());name=ctx['nodes'][ctx['roots'][0]]['metadata']['mangled'];assert name in names,name;print(name)
else:raise SystemExit(2)
