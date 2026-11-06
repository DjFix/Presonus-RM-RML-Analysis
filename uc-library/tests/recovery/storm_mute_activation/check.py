import json,subprocess,sys,os,tempfile,importlib.util
from pathlib import Path
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('provider',R/'uc-library/tests/recovery/file_mute_activation/check.py');provider=importlib.util.module_from_spec(spec);spec.loader.exec_module(provider)
OUT=R/'temp/recovery-work/storm-activation172';OUT.mkdir(parents=True,exist_ok=True);EXE=OUT/'replay'
SOURCES=['uc-library/src/Presonus/MuteGroupActivation.cpp','uc-library/src/Presonus/StormMuteActivation.cpp','uc-library/src/Presonus/StormMuteGroupComponent.cpp']
HEADERS=['uc-library/include/presonus/'+n+'.hpp' for n in ['MuteGroupBase','FileMuteGroup','StormMuteGroupComponent']]
DRIVER='uc-library/tests/recovery/StormMuteActivationReplay.cpp'
COMPILE=provider.COMPILE.copy();COMPILE[COMPILE.index(provider.DRIVER)]=DRIVER
idx=COMPILE.index(provider.LIB+'libcorelib.a');COMPILE[idx:idx]=SOURCES+['temp/core-upstream/root-integration-01/libpresonus_uc.a'];COMPILE[-1]=str(EXE)
def run(argv,**kw):
 print(json.dumps(argv),flush=True);p=subprocess.run(argv,cwd=R,text=True,capture_output=True,env={**os.environ,'TMPDIR':str(OUT)},**kw)
 print(p.stdout+p.stderr);p.check_returncode();return p.stdout
if __name__=='__main__':
 mode=sys.argv[1]
 if mode=='compile':run(COMPILE)
 elif mode=='format':run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror']+SOURCES+HEADERS+[DRIVER])
 elif mode=='symbols':
  out=run(['/usr/bin/nm','--defined-only',str(EXE)]);symbols={l.split()[-1] for l in out.splitlines()}
  import native
  assert all(n in symbols for n in native.NAMES)
 elif mode=='native':
  import native
  data=json.loads((T/'fixtures.json').read_text());assert data['ranges']==native.RANGES and data['cases']==native.cases();print(len(data['cases']),'fresh native executions match')
 elif mode=='replay':
  exe=sys.argv[2] if len(sys.argv)>2 else str(EXE)
  with tempfile.TemporaryDirectory(prefix='cases-',dir=OUT) as folder:out=run([exe,folder])
  native_cases=[c for c in json.loads((T/'fixtures.json').read_text())['cases'] if not c['base'] and not c['null'] and not c['abort']]
  lines=[l.split()[1:] for l in out.splitlines() if l.startswith('dispatch ')]
  assert len(lines)==len(native_cases)==24
  for line,c in zip(lines,native_cases):
   index,count,sentinel,first,last,status=map(int,line)
   assert [index,count,sentinel]==[c['index'],c['count'],int(c['sentinel'])]
   selected=[e[1] for e in c['events'] if e[0]=='activate']
   assert first==selected.count(0) and last==selected.count(256)
   assert status==len([e for e in c['events'] if e[0]=='status'])
  print('24 C++ selected-object/status observations matched independent original fixture')
 elif mode=='legacy':
  command=provider.COMPILE.copy();command[command.index(provider.DRIVER)]='uc-library/tests/recovery/reconstruction-200-02/large02_w09/driver.cpp'
  i=command.index(provider.LIB+'libcorelib.a');command[i:i]=['uc-library/src/Presonus/MuteGroupActivation.cpp','temp/core-upstream/root-integration-01/libpresonus_uc.a']
  command[-1]=str(OUT/'legacy');command.insert(-2,'-Wl,--wrap=_ZdlPv');command.insert(-2,'-Wl,--wrap=_ZdlPvm')
  command=[x for x in command if '--wrap=_ZN4Core8Portable' not in x];run(command)
  cases=[c for c in json.loads((R/'uc-library/tests/recovery/reconstruction-200-02/large02_w09/fixtures.json').read_text())['cases'] if c['command'].split()[0] in ['cache','cachef','param','filector'] or c['command'].startswith('destroy file')]
  lines=run([str(OUT/'legacy')],input=''.join(c['command']+'\n' for c in cases)).splitlines();assert len(lines)==len(cases)
  for c,line in zip(cases,lines):assert list(map(float,line.split()))==c['expected'],(c,line)
  print(len(cases),'historical lifecycle cases passed')
 else:raise SystemExit(mode)
