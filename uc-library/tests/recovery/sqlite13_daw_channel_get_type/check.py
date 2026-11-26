"""Linux bounded native/provider reconstruction checks; all argv retained."""
import argparse,importlib.util,json,subprocess,sys,hashlib,datetime
from pathlib import Path
TEST=Path(__file__).parent
TASK=TEST.name
PACKET=Path('temp/recovery-work/sqlite-issued/packet-sol61')/TASK/'CONTEXT.json'
SOURCES=[Path('uc-library/src/Presonus')/name for name in ('DAWChannel.cpp','DAWChannelInit.cpp','DAWChannelGroup.cpp','DAWChannelGroupInit.cpp','DAWDeviceFolder.cpp','DAWDeviceSlot.cpp')]+[Path('uc-library/src/Presonus/UC/ClientComponent.cpp'),Path('uc-library/src/mixer_dsp/Formatters.cpp'),Path('uc-library/src/mixer_dsp/Power.cpp')]
OWNED=[Path('uc-library/include/presonus/DAWChannel.hpp'),Path('uc-library/include/presonus/DAWChannelGroup.hpp'),SOURCES[0],SOURCES[3],TEST/'Replay.cpp']
BUILD=Path('temp/recovery-work/sol61-local')/TASK
CORE=Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a')
ALLOC=CORE.with_name('libpresonus_core_allocator.a')
FLAGS=['g++','-std=c++17','-O2','-Ulinux','-Wno-multichar','-Iuc-library/include','-Ithird_party/ccl-framework','-ffunction-sections','-fdata-sections']
def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['format','compile','symbols','replay']);parser.add_argument('--exe',type=Path);args=parser.parse_args()
 BUILD.mkdir(parents=True,exist_ok=True);commands=[]
 def invoke(argv):
  argv=list(map(str,argv));r=subprocess.run(argv,text=True,capture_output=True);commands.append(dict(argv=argv,exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr));
  if r.returncode: print(r.stdout,r.stderr,file=sys.stderr)
  (BUILD/(args.mode+'.json')).write_text(json.dumps(dict(commands=commands),indent=2)+'\n');r.check_returncode();return r.stdout
 if args.mode=='format':
  print(invoke(['uc-library/.venv/bin/clang-format','--version']).strip())
  invoke(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*OWNED])
 elif args.mode=='compile':
  objects=[]
  for source in [*SOURCES,TEST/'Replay.cpp']:
   obj=BUILD/(source.stem+'.o');invoke([*FLAGS,'-MMD','-c',source,'-o',obj]);objects.append(obj)
  link=['g++',*objects,CORE,ALLOC,'-pthread','-Wl,--gc-sections']
  if TASK.endswith('group_idle'): link+=['-Wl,--wrap=_ZN4Core8Portable9Component6onIdleEv']
  invoke([*link,'-o',BUILD/'Replay'])
 elif args.mode=='symbols':
  packet=json.loads(PACKET.read_text());mangled=packet['originals'][0]['original']['mangled']
  obj=BUILD/('DAWChannel.o' if TASK.endswith('get_type') else 'DAWChannelGroupInit.o')
  symbols=invoke(['nm','--defined-only',obj]);assert mangled in {line.split()[-1] for line in symbols.splitlines()};print(mangled)
  sized=invoke(['nm','-S','--defined-only',obj]);sizes={line.split()[-1]:int(line.split()[1],16) for line in sized.splitlines() if len(line.split())==4};assert sizes['_ZZNK8Presonus10DAWChannel7getTypeEvE6buffer']==32;assert sizes['_ZZNK8Presonus10DAWChannel5getIDEvE6buffer']==64
 else:
  spec=importlib.util.spec_from_file_location('task_native',TEST/'native.py');native=importlib.util.module_from_spec(spec);sys.modules[spec.name]=native;spec.loader.exec_module(native)
  fixture=json.loads((TEST/'fixtures.json').read_text());assert native.run(PACKET)==fixture
  exe=args.exe or BUILD/'Replay'
  for role in fixture:
   if TASK.endswith('get_type'):
    expected=['null' if c['input'] is None else c['input'][:31] for c in role['cases']]
    assert invoke([exe.resolve()]).splitlines()==expected
   else:
    for case in role['cases']:
     inputs=[case['value'],case['count']] if TASK.endswith('group_idle') else [case['flag'],case['count']]
     output=invoke([exe.resolve(),*inputs]).splitlines();assert output==case['expected'],(output,case['expected'])
  print('Both native ranges re-executed and portable observations matched')
 (BUILD/(args.mode+'.json')).write_text(json.dumps(dict(mode=args.mode,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),commands=commands),indent=2)+'\n')
if __name__=='__main__':main()
