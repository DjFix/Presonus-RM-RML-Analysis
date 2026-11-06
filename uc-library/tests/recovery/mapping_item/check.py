"""Standalone acceptance commands; production integration remains Root-owned."""
import hashlib, importlib.util, json, os, pathlib, subprocess, sys
ROOT=pathlib.Path(__file__).resolve().parents[4]
os.chdir(ROOT)
HERE=pathlib.Path('uc-library/tests/recovery/mapping_item')
OUT=pathlib.Path('temp/recovery-work/mapping157-local');OUT.mkdir(parents=True,exist_ok=True)
SOURCES=['uc-library/include/presonus/MappingTable.hpp','uc-library/src/Presonus/MappingTableItem.cpp','uc-library/tests/recovery/MappingItemReplay.cpp']
BINARY=OUT/'MappingItemReplay'
WRAPS=['_ZN8Presonus5Panel10LEDControl12setBlinkModeENS1_9BlinkModeE','_ZN8Presonus5Panel10LEDControl14setInverseModeEb']
def command(argv):
 print(json.dumps(argv),flush=True)
 subprocess.run(argv,check=True,env=dict(os.environ,TMPDIR=str(ROOT/OUT)))
def main():
 kind=sys.argv[1]
 if kind=='format':
  command(['uc-library/.venv/bin/clang-format','--version'])
  command(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*SOURCES])
 elif kind=='compile':
  command(['g++','-std=c++17','-DNDEBUG','-O0','-Wno-multichar','-Iuc-library/include','-Ithird_party/ccl-framework',SOURCES[1],SOURCES[2],'uc-library/src/Presonus/Panel/control.cpp','uc-library/src/Presonus/Panel/LEDControlLifecycle.cpp','uc-library/src/surface_panel/LEDState.cpp','-Wl,--start-group','temp/core-upstream/root-integration-01/libpresonus_uc.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','-Wl,--end-group',*['-Wl,--wrap='+s for s in WRAPS],'-lpthread','-ldl','-lrt','-o',str(BINARY)])
 elif kind=='regression':
  for source in ['uc-library/src/Presonus/MappingTable.cpp','uc-library/src/Presonus/MappingTableConnect.cpp','uc-library/src/Presonus/MappingTableHardwareParameter.cpp']:
   command(['g++','-std=c++17','-DNDEBUG','-Wno-multichar','-Iuc-library/include','-Ithird_party/ccl-framework','-c',source,'-o',str(OUT/(pathlib.Path(source).stem+'.o'))])
  executable=OUT/'MappingRegression'
  command(['g++','-std=c++20','-DNDEBUG','-Wno-multichar','-Iuc-library/include','-Ithird_party/ccl-framework','uc-library/tests/recovery/stabilized01_mapping/driver.cpp','third_party/ccl-framework/core/malloc/coremalloc.cpp','-Wl,--start-group','temp/core-upstream/root-integration-01/libpresonus_uc.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','-Wl,--end-group','-lpthread','-ldl','-lrt','-lz','-o',str(executable)])
  command(['uc-library/.venv/bin/python','uc-library/tests/recovery/stabilized01_mapping/replay.py','--driver',str(executable),'--fixtures','uc-library/tests/recovery/stabilized01_mapping/fixtures.json'])
 elif kind=='symbols':
  output=subprocess.check_output(['nm','--defined-only',str(BINARY)],text=True)
  names={line.split()[-1] for line in output.splitlines() if line.split()}
  prefix='_ZN8Presonus12MappingTable4Item'
  expected=[prefix+'12setBlinkModeEPKc',prefix+'14setInverseModeEb',prefix+'C1EPKcPN4Core8Portable10AliasParamE',prefix+'C2EPKcPN4Core8Portable10AliasParamE']
  assert set(expected)<=names,set(expected)-names
  print('\n'.join(line for line in output.splitlines() if any(line.endswith(s) for s in expected)))
  print('PASS four exact original symbols, Linux ELF decoration')
 elif kind=='replay':
  spec=importlib.util.spec_from_file_location('native',ROOT/HERE/'native.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  fixture=json.loads((HERE/'fixtures.json').read_text());assert m.generate()==fixture,'Native fixtures changed'
  rows=[]
  for c in fixture['cases']:
   for initial in ([0,1,2,3,9] if c['op'] in ('B','I') else [0]):
    rows.append(' '.join([c['op'],str(int(c['text'] is None)),json.dumps(c['text'] or ''),str(c['control']),str(c['argument']),str(c['dispatch'][0] if c['dispatch'] else -1),str(initial),json.dumps(''.join(t+';' for t in c['trace']))]))
  driver=pathlib.Path(sys.argv[sys.argv.index('--driver')+1]) if '--driver' in sys.argv else BINARY
  result=subprocess.run([str(driver)],input='\n'.join(rows)+'\n',text=True,capture_output=True)
  print(result.stdout,end='');print(result.stderr,end='');assert result.returncode==0,result.returncode
  print('Native ARM cases:',len(fixture['cases']),'provider-composed replay cases:',len(rows))
 else:raise SystemExit(2)
if __name__=='__main__':main()
