"""Scoped replay adapter and fresh proof producer; never updates registry/integration."""
import argparse,datetime,hashlib,json,os,pathlib,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[4]
HERE=pathlib.Path(__file__).resolve().parent
DIR=HERE.relative_to(ROOT).as_posix()
CANONICAL=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis')
WORK='temp/recovery-work/compact20_surface_network-implementation'
EXE=WORK+'/Replay'
SOURCES=['uc-library/src/Presonus/Surface/TBRoutingPageComponent.cpp','uc-library/src/Presonus/Surface/SurfaceOutputComponent.cpp']
HEADERS=['uc-library/include/presonus/surface/TBRoutingPageComponent.hpp','uc-library/include/presonus/surface/SurfaceOutputComponent.hpp']
DEPENDENCIES=['uc-library/src/Presonus/Surface/MixerPageComponent.cpp','uc-library/src/Presonus/Surface/SurfaceChannelComponent.cpp']
DEPENDENCY_HEADERS=['uc-library/include/presonus/surface/MixerPageComponent.hpp','uc-library/include/presonus/surface/SurfaceChannelComponent.hpp']
CPP=SOURCES+[DIR+'/Replay.cpp']
FORMAT=HEADERS+CPP
PROVIDERS=['third_party/ccl-framework/core/portable/corecomponent.h','third_party/ccl-framework/core/portable/corecomponent.cpp','third_party/ccl-framework/core/portable/coreparams.h','third_party/ccl-framework/core/portable/coreparams.cpp','third_party/ccl-framework/core/public/corevector.h','third_party/ccl-framework/core/public/corebitset.h']
TASKS=(2,3,4,5,11,12)
def digest(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def bindings(paths):return {p:digest(ROOT/p) for p in paths}
COMMANDS=[]
def run(argv):
 begin=time.monotonic();start=datetime.datetime.now(datetime.timezone.utc).isoformat()
 result=subprocess.run([str(x) for x in argv],cwd=ROOT,capture_output=True,text=True,env={**os.environ,'TMPDIR':str(ROOT/WORK)})
 COMMANDS.append(dict(argv=[str(x) for x in argv],start_utc=start,seconds=time.monotonic()-begin,returncode=result.returncode,stdout=result.stdout,stderr=result.stderr))
 if result.returncode:raise RuntimeError(json.dumps(COMMANDS[-1]))
 return result.stdout
def compile_local():
 (ROOT/WORK).mkdir(parents=True,exist_ok=True)
 flags=['/usr/bin/c++','-std=c++20','-O0','-g','-fno-rtti','-fno-lto','-ffunction-sections','-fdata-sections','-Ulinux','-Wno-multichar','-UNDEBUG','-pthread','-Iuc-library/include','-Ithird_party/ccl-framework']
 objects=[]
 for source in CPP+DEPENDENCIES:
  out=WORK+'/'+pathlib.Path(source).stem+'.o';run(flags+['-c',source,'-o',out]);objects.append(out)
 baseline='temp/provider-baseline08/'
 libs=[baseline+'libpresonus_cs18_components.a',baseline+'libcorelib.a',baseline+'libpresonus_core_allocator.a']
 extra=CANONICAL/'temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a'
 run(['/usr/bin/c++',*objects,'-Wl,--gc-sections','-Wl,--start-group',*libs,'-Wl,--end-group',str(extra),'/usr/lib/x86_64-linux-gnu/libpng16.so.16','/usr/lib/x86_64-linux-gnu/libz.so.1','-lssl','-lcrypto','-ldl','-lm','-pthread','-o',EXE])
 receipt=dict(commands=COMMANDS,objects=bindings(objects),archives=bindings(libs),sources=bindings(CPP+DEPENDENCIES+HEADERS+DEPENDENCY_HEADERS),compiler=run(['/usr/bin/c++','--version']),built_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
 (ROOT/WORK/'compile-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 return objects,libs
def symbols(exe):
 lines=run(['/usr/bin/nm','--defined-only',exe]);names={x.split()[-1] for x in lines.splitlines() if x.split()}
 found={}
 for task in TASKS:
  p=ROOT/'temp/recovery-work/compact-10x20-20261113/generated-implementation40/prepared03/packets'/f'compact20_surface_network_{task:02}'/'request.json'
  t=json.loads(p.read_text())['targets'][0];assert t['mangled'] in names,t['mangled'];found[task]=t['mangled']
 return found
def replay(exe,fixtures,elf):
 sys.path.insert(0,str(HERE));from native import generate
 data=json.loads(pathlib.Path(fixtures).read_text());assert generate(elf)==data,'native fixtures changed'
 for i,case in enumerate(data['cases']):
  actual=run([exe,*case['argv']]);assert actual==case['expected'],(i,case,actual)
 return data
def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['format','compile','symbols','replay','proof']);p.add_argument('--executable',default=EXE);p.add_argument('--fixtures',default=DIR+'/fixtures.json');p.add_argument('--elf',default=str(CANONICAL/'rootfs/CS18_v13840/home/root/surface'));p.add_argument('--proof');p.add_argument('--integration-proof');p.add_argument('--object',action='append',default=[]);a=p.parse_args()
 (ROOT/WORK).mkdir(parents=True,exist_ok=True)
 if a.mode=='format':run([str(CANONICAL/'uc-library/.venv/bin/clang-format'),'--style=file','--fallback-style=LLVM','--dry-run','--Werror',*FORMAT])
 elif a.mode=='compile':compile_local()
 elif a.mode=='symbols':print(json.dumps(symbols(a.executable)))
 else:
  if a.mode=='proof':
   assert a.proof,'--proof new output path required';assert not pathlib.Path(a.proof).exists(),'proof output must be new'
  data=replay(a.executable,a.fixtures,a.elf);found=symbols(a.executable)
  counts={str(t):sum(c['task']==t for c in data['cases']) for t in TASKS}
  print(json.dumps(dict(cases=len(data['cases']),per_original_cases=counts,cpp_differential_passed=True)))
  if a.mode=='proof':
   format_version=run([str(CANONICAL/'uc-library/.venv/bin/clang-format'),'--version']).strip();run([str(CANONICAL/'uc-library/.venv/bin/clang-format'),'--style=file','--fallback-style=LLVM','--dry-run','--Werror',*FORMAT])
   proof=dict(version=1,producer=str(pathlib.Path(__file__).relative_to(ROOT)),producer_sha256=digest(__file__),produced_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),provider_thread_id=os.getenv('CODEX_THREAD_ID'),implementation_start_utc='2026-11-13T17:24:29.060277+00:00',implementation_end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),cpp_differential_passed=True,arm_differential_passed=False,compiled_mangled_names_matched=True,cpp_compiled=True,mangling_namespace_checked=True,functions=[dict(original_elf_sha256=data['elf_sha256'],mangled=found[t],cases=counts[str(t)],domain='Original app control-flow/provider-boundary observations plus separately executed actual CCL portable provider/lifecycle behavior; normal initialized state only',native_range=next(r for r in data['ranges'] if r['task']==t),cpp_differential_passed=True) for t in TASKS],sources=bindings(FORMAT+DEPENDENCIES+DEPENDENCY_HEADERS+[DIR+'/native.py',DIR+'/check.py',DIR+'/fixtures.json']),repository_sources=bindings(PROVIDERS),formatter=dict(version=format_version,paths=bindings(FORMAT)),executable=dict(path=a.executable,sha256=digest(ROOT/a.executable if not pathlib.Path(a.executable).is_absolute() else a.executable)),native_fixture=dict(path=a.fixtures,sha256=digest(ROOT/a.fixtures if not pathlib.Path(a.fixtures).is_absolute() else a.fixtures),oracle_scope=data['oracle_scope']),commands=COMMANDS,limitations=data['exclusions']+['CCL/runtime native bodies intercepted, not executed; actual CCL behaviors independently replayed','native D0 modeled allocator unmaps memory when native BL reaches allocator; host actual operator delete separately observed','ordinary method return types remain declaration-pending','D1/C++ class layout is intentional source port; no original hierarchy/layout proof'])
   if a.executable==EXE:
    receipt=json.loads((ROOT/WORK/'compile-receipt.json').read_text())
    assert receipt['sources']==bindings(CPP+DEPENDENCIES+HEADERS+DEPENDENCY_HEADERS),'local compile receipt stale'
    assert receipt['objects']==bindings(receipt['objects']),'object bytes changed'
    proof['actual_compile']=receipt
   if a.object:
    proof['canonical_objects']={path:digest(path) for path in a.object}
    for path in a.object:run(['/usr/bin/nm','--defined-only',path])
   if a.integration_proof:proof['fresh_integration_reference']={'path':a.integration_proof,'sha256':digest(a.integration_proof)}
   pathlib.Path(a.proof).parent.mkdir(parents=True,exist_ok=True);pathlib.Path(a.proof).write_text(json.dumps(proof,indent=2)+'\n')
if __name__=='__main__':main()
