"""Local replay checks; Root supplies canonical CTest built executable explicitly."""
import json,pathlib,subprocess,sys,os
ROOT=pathlib.Path(__file__).resolve().parents[4];TEST=pathlib.Path(__file__).parent
OUT=ROOT/'temp/recovery-work/rolling200-02/rack-network15';EXE=OUT/'replay'
FILES=['uc-library/include/presonus/panel/RackPanelComponent.hpp','uc-library/src/Presonus/Panel/RackPanelComponent.cpp','uc-library/include/presonus/panel/PanelTask.hpp','uc-library/src/Presonus/Panel/PanelTask.cpp','uc-library/include/presonus/panel/LEDNotifyTask.hpp','uc-library/src/Presonus/Panel/LEDNotifyTask.cpp','uc-library/tests/recovery/RackNetworkTasksReplay.cpp']
SOURCES=[FILES[i] for i in [1,3,5,6]]+['uc-library/src/Presonus/Panel/PanelComponentLifecycle.cpp','uc-library/src/Presonus/Panel/control.cpp','uc-library/src/Presonus/Panel/param_edit_handler.cpp','uc-library/src/Presonus/DelayTimer.cpp','uc-library/src/Presonus/DICE/PacketClockGateway.cpp']
LIB='temp/core-upstream/root-integration-01/upstream-core/sdk/lib/'
COMPILE=['/usr/bin/c++','-std=c++17','-O0','-fno-rtti','-ffunction-sections','-fdata-sections','-Wno-multichar','-Iuc-library/include','-Ithird_party/ccl-framework']+SOURCES+[LIB+'libcorelib.a',LIB+'libpresonus_core_allocator.a','-Wl,--gc-sections','-Wl,--wrap=_ZN8presonus4dice19packetClockRawTicksEv','-lpthread','-ldl','-o',str(EXE.relative_to(ROOT))]
def run(argv,**kw):
 print(json.dumps(list(map(str,argv))),flush=True)
 p=subprocess.run(list(map(str,argv)),cwd=ROOT,capture_output=True,text=True,env={**os.environ,'TMPDIR':str(OUT)},**kw)
 if p.returncode:print(p.stdout+p.stderr);p.check_returncode()
 return p.stdout

def replay(exe,fixture):
 cases=json.load(open(fixture))['cases'];lines=[]
 for case in cases:
  c=case['input'];values=[c[k] for k in ['target','ns','start','delay','flags','mask','n','m','k']]+[len(c['tasks']),len(c['queue']),c['append'],c['mutate']]
  values += [v for task in c['tasks'] for v in task]+c['queue'];lines.append(' '.join(map(str,values)))
 observed=run([str(exe)],input='\n'.join(lines)+'\n').splitlines();observed=[s for s in observed if not s.startswith('RackPanelComponent::')]
 assert len(observed)==len(cases),(len(observed),len(cases))
 for i,(case,line) in enumerate(zip(cases,observed)):
  trace,tail=line.split('|');words=trace.split();exp=case['expected'];assert int(words[0])==len(exp['trace']) and words[1:]==exp['trace'],(i,case,line)
  values=list(map(int,tail.split()));expect=[exp['flags'],exp.get('result',-1),len(exp['queue'])]+exp['queue']+[len(exp['created'])]+[int(v) for task in exp['created'] for v in task]
  assert values==expect,(i,case,line,expect)
 print('PASS',len(cases),'actual C++ executions match independent ARM observations; exact flags, strict deadlines, signed wrap, nullable parameters, ordered controls, provider edits, duplicate pointers, deferred removal and callback appends')
 print(run([str(exe),'provider']))
if __name__=='__main__':
 OUT.mkdir(parents=True,exist_ok=True);mode=sys.argv[1]
 if mode=='format':print(run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror']+FILES))
 elif mode=='compile':print(run(COMPILE))
 elif mode=='symbols':
  symbols={r.split()[-1] for r in run(['/usr/bin/nm','--defined-only',str(EXE)]).splitlines() if r.split()}
  for i in [1,2,3,4,6,13]:
   p=ROOT/f'temp/recovery-work/rolling200-02/next-implementation15/prepared-rack-network15/packets/rolling200_02_rack_network15_{i:02}/request.json';name=json.load(open(p))['targets'][0]['mangled'];assert name in symbols,name;print(name)
 elif mode=='replay':replay(pathlib.Path(sys.argv[2]).resolve() if len(sys.argv)>2 else EXE,pathlib.Path(sys.argv[3]) if len(sys.argv)>3 else TEST/'fixtures.json')
 elif mode=='regressions':
  # Keep current production dependencies, replace the one test translation unit.
  base=[x for x in COMPILE[:COMPILE.index('-o')] if x!='uc-library/tests/recovery/RackNetworkTasksReplay.cpp' and x!='-Wl,--wrap=_ZN8presonus4dice19packetClockRawTicksEv']
  # Rebuild each provider from current source; no historical executable is reused.
  base+=['-lz']
  index=base.index(LIB+'libcorelib.a');base[index:index]=['uc-library/src/Presonus/Panel/LEDControlLifecycle.cpp','uc-library/src/surface_panel/LEDState.cpp','uc-library/src/surface_panel/ControlGroup.cpp']
  def regargv(extra):
   index=base.index(LIB+'libcorelib.a');return base[:index]+extra+base[index:]
  exe=OUT/'legacy-rack'
  print(run(regargv(['uc-library/tests/graph_trial07_rackpanel_tests.cpp'])+['-o',str(exe)]))
  print(run(['uc-library/.venv/bin/python','uc-library/tests/recovery/trial07/rackpanel/replay.py','--executable',str(exe),'--fixtures','uc-library/tests/recovery/trial07/rackpanel/fixtures.json']))
  owner=OUT/'owners'
  print(run(regargv(['uc-library/src/Presonus/Panel/FrontPanelLifecycle.cpp','uc-library/tests/recovery/PanelOwnerRegression.cpp'])+['-o',str(owner)]))
  print(run([str(owner)]))
  lifecycle=OUT/'lifecycle'
  print(run(regargv(['uc-library/tests/recovery/RackPanelLifecycleReplay.cpp'])+['-Wl,--wrap=_ZN8Presonus10DelayTimerD1Ev','-Wl,--wrap=_ZN8Presonus5Panel14PanelComponentD2Ev','-o',str(lifecycle)]))
  fixture=ROOT/'uc-library/candidates/rolling200_02_rack_lifecycle/fixtures.json'
  producer=ROOT/'uc-library/candidates/rolling200_02_rack_lifecycle/check.py'
  if not fixture.exists() or not producer.exists():raise SystemExit('Missing transported Rack lifecycle producer/fixtures; executables compiled, owner and trial07 replay completed')
  print(run(['uc-library/.venv/bin/python',str(producer),'replay','--executable',str(lifecycle),'--owners',str(owner),'--fixtures',str(fixture)]))
  # The earlier four Rack method replay instruments only the current Rack TU.
  obj=OUT/'rack-instrumented.o'
  print(run(COMPILE[:COMPILE.index(SOURCES[0])]+['-finstrument-functions','-c',SOURCES[0],'-o',str(obj)]))
  older=OUT/'rack-four'
  extra=['uc-library/candidates/rolling200_02_rack_panel/replay.cpp','uc-library/src/Presonus/Mixer/MixerComponentBase.cpp','uc-library/src/Presonus/Mixer/PermissionsComponent.cpp','-DRACK_PANEL_INSTRUMENTED_REPLAY=1','-Wl,--wrap=clock_gettime','-Wl,--wrap=_ZN8Presonus5Mixer18MixerComponentBase18resetPermissionsPWEv']
  oldcmd=[x for x in regargv(extra) if x!=SOURCES[0]]
  oldcmd.insert(oldcmd.index('uc-library/src/Presonus/Panel/PanelTask.cpp'),str(obj))
  print(run(oldcmd+['-o',str(older)]))
  print(run(['uc-library/.venv/bin/python','uc-library/candidates/rolling200_02_rack_panel/check.py','replay',str(older)]))

 elif mode=='native':
  import native
  actual=native.produce();saved=json.load(open(TEST/'fixtures.json'));assert json.loads(json.dumps(actual))==saved
  (OUT/'native-pc-audit-replay.json').write_text(json.dumps(native.AUDIT,indent=2)+'\n');print('Fresh native cases reproduce fixtures:',native.AUDIT['cases'])
 else:raise SystemExit('Unknown mode')
