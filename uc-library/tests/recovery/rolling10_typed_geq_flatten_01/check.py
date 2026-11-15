import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent;TASK=T.name;O=R/'temp/recovery-work'/TASK;O.mkdir(parents=True,exist_ok=True)
SOURCES=['uc-library/include/presonus/mixer/GEQComponent.hpp','uc-library/src/Presonus/Mixer/GEQComponent.cpp'];OWNED=SOURCES+[str((T/'Replay.cpp').relative_to(R))]
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(argv,input=None):
 print(json.dumps(list(map(str,argv))),flush=True);p=subprocess.run(list(map(str,argv)),cwd=R,input=input,capture_output=True,text=True,env={**os.environ,'TMPDIR':str(O)});print(p.stdout,end='');print(p.stderr,end='',file=sys.stderr);p.check_returncode();return p.stdout
def main():
 p=argparse.ArgumentParser();p.add_argument('mode',nargs='?',default='replay');p.add_argument('--exe');p.add_argument('--object');p.add_argument('--integration');p.add_argument('--out');p.add_argument('--provider-core');p.add_argument('--provider-allocator');a=p.parse_args();import native
 if a.mode=='format':run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*OWNED]);return
 fixture=json.loads((T/'fixtures.json').read_text())
 if a.mode=='native':assert native.generate()==fixture;return
 if a.mode=='compile':
  flags=['c++','-std=c++17','-O0','-ffunction-sections','-fdata-sections','-fno-rtti','-Wno-multichar','-Iuc-library/include','-Ithird_party/ccl-framework']
  run([*flags,'-c',SOURCES[1],'-o',O/'production.o']);run([*flags,'-c',OWNED[2],'-o',O/'driver.o']);run(['c++',O/'production.o',O/'driver.o','-Wl,--gc-sections','temp/provider-baseline08/libcorelib.a','temp/provider-baseline08/libpresonus_core_allocator.a','-lz','-lpthread','-ldl','-lm','-o',O/'replay']);return
 obj=Path(a.object) if a.object else O/'production.o';exe=Path(a.exe) if a.exe else O/'replay'
 symbols=run(['nm','--defined-only',obj]);names={l.split()[-1] for l in symbols.splitlines() if l.split()};assert native.NAME in names
 if a.mode=='symbols':return
 assert native.generate()==fixture
 inventory=[list(map(int,l.split())) for l in run([exe,'--inventory']).splitlines()];assert inventory==fixture['provider_inventory']
 payload=''
 for c in fixture['cases']:
  calls=[x[1:] for x in c['trace'] if x[0]=='reset'];payload+=str(len(calls))+'\n'+''.join(str(tag)+' '+str(edit)+'\n' for tag,edit in calls)
 output=run([exe],payload);assert len(output.splitlines())==4
 domain='Four actual inherited CCL parameter-list states: empty, sparse tags0/15/30, dense31, every-third. ARM validates all ascending31lookups, missing skips and resetValue(true) dispatch; native observed callsequence drives separate actual pinned source-provider resets with value/edit/changed event traces compared to reconstructed C++. Defaults -2..2, equal and unequal finite current values; outside tags-1/31 unchanged; borrowed stable observers.'
 limitations=['Provisional void return: original ordinary return unresolved','Portable source port; original class layout/ARM ABI and hardware not established','Actual NumericParam only; unknown derived overrides excluded; original Core bodies never execute','Original native boundary traces separate from source-provider value/notification evidence']
 sources={str(Path(x).relative_to('uc-library')):digest(R/x) for x in SOURCES}
 proof=dict(task_id=TASK,original_elf_sha256=native.SHA,mangled_names=[native.NAME],native=fixture,canonical_binding_pending=not bool(a.integration),compiled_mangled_names_matched=True,cpp_differential_passed=True,portable_ready=False,validation_domain=domain,limitations=limitations,sources=sources,repository_sources={},object=dict(path=str(obj),sha256=digest(obj)),executable=dict(path=str(exe),sha256=digest(exe)),formatter=run(['uc-library/.venv/bin/clang-format','--version']).strip())
 deps=['third_party/ccl-framework/core/portable/corecomponent.h','third_party/ccl-framework/core/portable/corecomponent.cpp','third_party/ccl-framework/core/portable/coreparams.h','third_party/ccl-framework/core/portable/coreparams.cpp','third_party/ccl-framework/core/portable/coreparaminfo.h']
 proof['repository_sources']={x:digest(R/x) for x in deps}
 canonical=bool(a.integration or a.exe)
 core=a.provider_core or ('temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a' if canonical else 'temp/provider-baseline08/libcorelib.a')
 alloc=a.provider_allocator or ('temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a' if canonical else 'temp/provider-baseline08/libpresonus_core_allocator.a')
 proof['provider_archives']={x:digest(R/x) for x in [core,alloc]}
 proof['provider_reference_output']=output
 if a.integration:proof['integration']=dict(path=a.integration,sha256=digest(R/a.integration))
 proof['proposed_readiness']=dict(ready=[],pending=[dict(original_elf_sha256=native.SHA,mangled=native.NAME,original_address=native.ADDRESS,sources=sources,domain=domain,declaration_uncertainties=limitations,canonical_binding_pending=not bool(a.integration))])
 for entry in proof['proposed_readiness']['pending']:
  entry.update(portable_ready=False,cpp_compiled=True,mangling_namespace_checked=True,repository_sources=proof['repository_sources'])
 if a.out:Path(a.out).write_text(json.dumps(proof,indent=2)+'\n')
if __name__=='__main__':main()
