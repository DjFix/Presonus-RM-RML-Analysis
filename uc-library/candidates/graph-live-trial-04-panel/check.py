import subprocess,sys,json,pathlib
root=pathlib.Path('uc-library/candidates/graph-live-trial-04-panel')
src=['uc-library/src/Presonus/Panel/PanelComponent.cpp','uc-library/include/presonus/panel/PanelComponent.hpp','uc-library/tests/graph_trial04_panel_tests.cpp']
exe='temp/recovery-work/graph-live-trial-04/panel-worker/replay'
mode=sys.argv[1]
if mode=='format':subprocess.run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*src],check=True)
if mode=='compile':subprocess.run(['c++','-std=c++17','-Iuc-library/include',src[0],src[2],'-o',exe],check=True)
if mode=='symbols':
 out=subprocess.check_output(['nm',exe],text=True)
 for i in range(1,6):
  req=json.load(open(f'temp/recovery-work/graph-live-trial-04/trial04_panel_{i}-packet/request.json'));assert req['targets'][0]['mangled'] in out
if mode=='replay':subprocess.run(['uc-library/.venv/bin/python',str(root/'replay.py'),exe],check=True)
