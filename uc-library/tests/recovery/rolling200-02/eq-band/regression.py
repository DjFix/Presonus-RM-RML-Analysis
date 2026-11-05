"""Replay existing immutable EQ getter, clearing and curve fixtures."""
import importlib.util,pathlib,subprocess,os
ROOT=pathlib.Path(__file__).resolve().parents[5]
OUT=ROOT/'temp/recovery-work/rolling200-02/eq-band';PY='uc-library/.venv/bin/python'
def run(argv):
 print(argv,flush=True);subprocess.run(list(map(str,argv)),cwd=ROOT,env={**os.environ,'TMPDIR':str(OUT)},check=True)
for group in ['eq-control','eq-curves']:
 base=pathlib.Path('uc-library/tests/recovery/rolling200-02')/group
 spec=importlib.util.spec_from_file_location(group,ROOT/base/'check.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 argv=m.COMPILE.copy();argv[-1]=str(OUT/(group+'-regression'));run(argv)
 if group=='eq-control':m.replay(OUT/(group+'-regression'),ROOT/base/'fixtures.json')
 else:
  run([PY,base/'replay_boundaries.py',OUT/(group+'-regression'),base/'fixtures.json'])
  run([PY,base/'replay_curves.py',OUT/(group+'-regression'),base/'curve-fixtures.json'])
base=pathlib.Path('uc-library/tests/recovery/trial08/eq')
exe=OUT/'getters-regression'
run(['/usr/bin/c++','-std=c++20','-fno-rtti','-Wno-multichar','-ffunction-sections','-fdata-sections','-Iuc-library/include','-Ithird_party/ccl-framework','uc-library/src/Presonus/EQControl.cpp','uc-library/src/Presonus/EQControlBandParams.cpp','uc-library/tests/graph_trial08_eq_tests.cpp','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a','-Wl,--gc-sections','-lz','-o',exe])
for name in ['fixtures.json','getter-fixtures.json','buffered-fixtures.json','provider-fixtures.json','parser-fixtures.json']:run([PY,base/'replay.py','--executable',exe,'--fixtures',base/name])
