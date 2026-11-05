"""Keep existing constructor, band, getter, curve and observer fixtures unchanged."""
import importlib.util,pathlib,subprocess,os,json,sys
ROOT=pathlib.Path(__file__).resolve().parents[5]
OUT=ROOT/'temp/recovery-work/rolling200-02/eq-lifecycle';OUT.mkdir(parents=True,exist_ok=True)
PY='uc-library/.venv/bin/python';LIB='temp/core-upstream/root-integration-01/upstream-core/sdk/lib/'
def run(argv):
 argv=list(map(str,argv));print(json.dumps(argv),flush=True)
 p=subprocess.run(argv,cwd=ROOT,env={**os.environ,'TMPDIR':str(OUT)},text=True,capture_output=True)
 print(p.stdout,end='');print(p.stderr,end='',file=sys.stderr);p.check_returncode();return p
for group in ['eq-constructors','eq-band','eq-control','eq-curves']:
 base=pathlib.Path('uc-library/tests/recovery/rolling200-02')/group
 spec=importlib.util.spec_from_file_location(group,ROOT/base/'check.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 argv=m.COMPILE.copy();argv[-1]=str(OUT/(group+'-regression'))
 extras=['-Iuc-library/src/mixer_dsp','-ffp-contract=off']
 for source in ['uc-library/src/Presonus/Dsp/EqSourceProviders.cpp','uc-library/src/mixer_dsp/Logarithm.cpp','temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a']:
  if source not in argv:extras.append(source)
 argv[argv.index(LIB+'libcorelib.a'):argv.index(LIB+'libcorelib.a')]=extras
 run(argv)
 if group=='eq-constructors':m.replay(pathlib.Path(argv[-1]),ROOT/base/'fixtures.json')
 elif group=='eq-band':run([PY,base/'check.py','replay','--executable',argv[-1]])
 elif group=='eq-control':m.replay(pathlib.Path(argv[-1]),ROOT/base/'fixtures.json')
 else:
  run([PY,base/'replay_boundaries.py',argv[-1],base/'fixtures.json'])
  run([PY,base/'replay_curves.py',argv[-1],base/'curve-fixtures.json'])
# Retain historical getter/provider coverage bound to the same canonical class.
base=pathlib.Path('uc-library/tests/recovery/trial08/eq')
exe=OUT/'getters-regression'
run(['/usr/bin/c++','-std=c++20','-fno-rtti','-Wno-multichar','-ffunction-sections','-fdata-sections','-Iuc-library/include','-Iuc-library/src/mixer_dsp','-Ithird_party/ccl-framework','uc-library/src/Presonus/EQControl.cpp','uc-library/src/Presonus/EQControlBandParams.cpp','uc-library/tests/graph_trial08_eq_tests.cpp','uc-library/src/Presonus/Dsp/EqSourceProviders.cpp','uc-library/src/mixer_dsp/Logarithm.cpp','temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a',LIB+'libcorelib.a',LIB+'libpresonus_core_allocator.a','-Wl,--gc-sections','-lz','-o',exe])
for name in ['fixtures.json','getter-fixtures.json','buffered-fixtures.json','provider-fixtures.json','parser-fixtures.json']:
 run([PY,base/'replay.py','--executable',exe,'--fixtures',base/name])
print('Unchanged constructor, band, getter, curve and observer fixtures all pass')
