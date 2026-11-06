"""Local checks; CTest must pass the canonical built executable explicitly."""
import json,pathlib,subprocess,sys,os
ROOT=pathlib.Path(__file__).resolve().parents[4];TEST=pathlib.Path(__file__).parent
OUT=ROOT/'temp/recovery-work/rolling200-02/rack-burnin135';EXE=OUT/'replay'
FILES=['uc-library/include/presonus/panel/RackPanelComponent.hpp','uc-library/include/presonus/panel/PanelRegistrar.hpp','uc-library/include/presonus/surface_panel/ControlHelpers.hpp','uc-library/src/Presonus/Panel/RackPanelBurnIn.cpp','uc-library/src/Presonus/Panel/ControlRegistrarCommands.cpp','uc-library/src/Presonus/Panel/PanelRegistrarDualMessage.cpp','uc-library/tests/recovery/RackPanelBurnInReplay.cpp']
SOURCES=FILES[3:6]+['uc-library/src/Presonus/Panel/RackPanelComponent.cpp','uc-library/src/Presonus/Panel/PanelRegistrar.cpp','uc-library/src/Presonus/Panel/PanelTask.cpp','uc-library/src/Presonus/Panel/LEDNotifyTask.cpp','uc-library/src/Presonus/Panel/PanelComponentLifecycle.cpp','uc-library/src/Presonus/Panel/control.cpp','uc-library/src/Presonus/Panel/param_edit_handler.cpp','uc-library/src/Presonus/DelayTimer.cpp','uc-library/src/Presonus/DICE/PacketClockGateway.cpp','uc-library/src/Presonus/Panel/protocol_comm.cpp','uc-library/src/Presonus/Panel/uart_protocol.cpp']
CC=['/usr/bin/c++','-std=c++17','-O0','-fno-rtti','-ffunction-sections','-fdata-sections','-Wno-multichar','-Iuc-library/include','-Ithird_party/ccl-framework']
LIB='temp/core-upstream/root-integration-01/upstream-core/sdk/lib/'
KEYS=['target','enabled','ns0','ns1','held','active','object','primary','secondary','secondary_present','mutate','derived']
def run(argv,**kw):
 print(json.dumps(list(map(str,argv))),flush=True)
 p=subprocess.run(list(map(str,argv)),cwd=ROOT,capture_output=True,text=True,env={**os.environ,'TMPDIR':str(OUT)},**kw)
 if p.returncode:print(p.stdout+p.stderr);p.check_returncode()
 return p.stdout

compile_code=compile
def compile():
 objects=[]
 for i,s in enumerate(SOURCES):
  obj=OUT/f'{i}.o';objects.append(str(obj.relative_to(ROOT)))
  instrument=['-finstrument-functions'] if s in SOURCES[:5] else []
  print(run(CC+instrument+['-c',s,'-o',obj]))
 print(run(CC+objects+['uc-library/tests/recovery/RackPanelBurnInReplay.cpp','-Wl,--start-group',LIB+'libcorelib.a',LIB+'libpresonus_core_allocator.a','temp/core-upstream/root-integration-01/libpresonus_uc.a','-Wl,--end-group','-Wl,--gc-sections','-Wl,--wrap=clock_gettime','-Wl,--wrap=_ZN4Core11DebugPrintfEPKcz','-lpthread','-ldl','-lz','-o',EXE]))

def replay(exe,fixture):
 data=json.load(open(fixture));frames=0
 for i,case in enumerate(data['cases']):
  text='\n'.join(' '.join(str(f[k]) for k in KEYS) for f in case['frames'])+'\n'
  output=run([exe],input=text).splitlines()
  actual=[s.split()[1:] for s in output if s.startswith('TRACE')]
  assert actual==case['expected'],(i,case,actual)
  # Full wire bytes originate in separately executed original UART encoder.
  expected=[]
  for events in case['expected']:
   for event in events:
    if event.startswith(('p:','s:')):
     name,h=event.split(':');b=bytes.fromhex(h)
     # Exact codec formatting is checked against native encoder fixtures below.
     expected.append((name,b))
  wires=[s.split()[1:] for s in output if s.startswith('WIRE')]
  assert len(wires)==len(expected),(i,wires,expected)
  for (name,wire),(en,b) in zip(wires,expected):
   assert name==en,(i,wires,expected)
   assert bytes.fromhex(wire)==wire_bytes(b),(i,b,bytes.fromhex(wire),wire_bytes(b))
  frames+=len(case['frames'])
 print(run([exe,'provider']))
 print('PASS',frames,'exact native frames; actual commands/dual route/clock/state/order and wire bytes')
def wire_bytes(b):
 # Values below originate in separately executed original UART encoder, bound
 # by seal.py. Do not derive oracle observations from portable implementation.
 enc=json.load(open(TEST/'fixtures.json'))['encoder']
 return bytes.fromhex(enc[b.hex()])
if __name__=='__main__':
 OUT.mkdir(parents=True,exist_ok=True);mode=sys.argv[1]
 if mode=='format':
  print(run(['uc-library/.venv/bin/clang-format','--version']))
  print(run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror']+FILES))
 elif mode=='compile':compile()
 elif mode=='symbols':
  symbols={x.split()[-1] for x in run(['/usr/bin/nm','--defined-only',EXE]).splitlines() if x.split()}
  for r in json.load(open(TEST/'fixtures.json'))['ranges']:
   assert r['mangled'] in symbols,r
   print(r['elf_sha256'],r['mangled'])
 elif mode=='replay':replay(pathlib.Path(sys.argv[2]).resolve() if len(sys.argv)>2 else EXE,pathlib.Path(sys.argv[3]) if len(sys.argv)>3 else TEST/'fixtures.json')
 elif mode=='native':
  import native
  actual=native.produce();saved=json.load(open(TEST/'fixtures.json'));assert actual==saved
  print('Fresh native observations match',native.AUDIT['frames'])
 elif mode=='regressions':
  # The old runner predates registrar virtual dispatch; compile its unchanged
  # replay against the newly required real command providers, in this adapter.
  old=ROOT/'uc-library/tests/recovery/rack_network_tasks/check.py'
  code=old.read_text().replace("LIB='", "SOURCES += "+repr(FILES[3:6]+['uc-library/src/Presonus/Panel/PanelRegistrar.cpp'])+"\nLIB='",1)
  code=code.replace("LIB+'libcorelib.a',LIB+'libpresonus_core_allocator.a'", "'-Wl,--start-group',LIB+'libcorelib.a',LIB+'libpresonus_core_allocator.a','temp/core-upstream/root-integration-01/libpresonus_uc.a','-Wl,--end-group','-lz'",1)
  for legacy_mode in ['compile','replay','regressions']:
   sys.argv=[str(old),legacy_mode]
   exec(compile_code(code,str(old),"exec"),{'__file__':str(old),'__name__':'__main__'})
 else:raise SystemExit(mode)
