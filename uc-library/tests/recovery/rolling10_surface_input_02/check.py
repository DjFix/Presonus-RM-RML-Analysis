import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[4]; T=Path(__file__).resolve().parent
TASK=T.name; O=R/'temp/recovery-work'/TASK;O.mkdir(parents=True,exist_ok=True)
OWNED=['uc-library/include/presonus/surface/SurfaceInputComponent.hpp','uc-library/src/Presonus/Surface/SurfaceInputComponent.cpp',str((T/'Replay.cpp').relative_to(R))]
FLAGS=['c++','-std=c++17','-fno-rtti','-Wno-multichar','-ffunction-sections','-fdata-sections','-Iuc-library/include','-Ithird_party/ccl-framework']
def run(argv):
 print(json.dumps(list(map(str,argv))),flush=True)
 p=subprocess.run(list(map(str,argv)),cwd=R,capture_output=True,text=True,env={**os.environ,'TMPDIR':str(O)})
 print(p.stdout,end='');print(p.stderr,end='',file=sys.stderr);p.check_returncode();return p.stdout
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('mode',nargs='?',default='replay');p.add_argument('--exe');p.add_argument('--object');p.add_argument('--integration');p.add_argument('--out');p.add_argument('--provider-core');p.add_argument('--provider-allocator');a=p.parse_args()
 import native
 if a.mode=='format':run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*OWNED]);return
 if a.mode=='native':assert native.generate()==json.loads((T/'fixtures.json').read_text());return
 if a.mode=='compile':
  for source,obj in [(OWNED[1],'production.o'),('uc-library/src/Presonus/Surface/SurfaceChannelComponent.cpp','channel.o'),(OWNED[2],'driver.o')]:run([*FLAGS,'-O2','-c',source,'-o',O/obj])
  run(['c++',O/'production.o',O/'channel.o',O/'driver.o','-Wl,--gc-sections','temp/provider-baseline08/libcorelib.a','temp/provider-baseline08/libpresonus_core_allocator.a','-lz','-lpthread','-ldl','-lm','-o',O/'replay']);return
 obj=Path(a.object) if a.object else O/'production.o';exe=Path(a.exe) if a.exe else O/'replay'
 symbols=run(['nm','--defined-only',obj]);assert native.NAME in {l.split()[-1] for l in symbols.splitlines() if l.split()}
 if a.mode=='symbols':return
 assert native.generate()==json.loads((T/'fixtures.json').read_text())
 observed=run([exe]); expected='0 0\n1 '+('1' if native.TAG==301 else '0')+'\n2 1\n3 1\n';assert observed==expected,(observed,expected)
 proof={'task_id':TASK,'canonical_binding_pending':not bool(a.integration),'native':json.loads((T/'fixtures.json').read_text()),'provider_cases':4,'repeated_queries':32,'object':{'path':str(obj),'sha256':digest(obj)},'executable':{'path':str(exe),'sha256':digest(exe)},'integration':a.integration,'formatter':run(['uc-library/.venv/bin/clang-format','--version']).strip(),'validation_domain':'Four actual CCL parameter-list prefix states: empty, tag301 only, both tags, unrelated extra; 8 repeated const queries each. Four ARM provider return bit patterns including null. Core boundary modeled; actual CCL executes separately.','limitations':['Original unencoded return declaration unresolved; provisional Parameter* source port','Original class layout and ARM ABI not established','No Core firmware executes; tail boundary modeled; no hardware validation'],'sources':{x:digest(R/x) for x in OWNED}}
 proof.update(original_elf_sha256=native.SHA,mangled_names=[native.NAME],compiled_mangled_names_matched=True,cpp_differential_passed=True,portable_ready=True)
 proof['sources']={str(Path(k).relative_to('uc-library')):v for k,v in proof['sources'].items()}
 deps=['third_party/ccl-framework/core/portable/corecomponent.h','third_party/ccl-framework/core/portable/corecomponent.cpp','third_party/ccl-framework/core/portable/coreparams.h','third_party/ccl-framework/core/portable/coreparams.cpp','third_party/ccl-framework/core/portable/coreparaminfo.h']
 proof['repository_sources']={x:digest(R/x) for x in deps}
 proof['local_provider_archive_provenance']={'temp/provider-baseline08/libcorelib.a': '3c4f0825acb529fda135587b7ff5cb92ca0100bb417a20c034d3fdef80a93e0c', 'temp/provider-baseline08/libpresonus_core_allocator.a': '69892fbcec9a50a140462982073c686a67ca4763dfb5dfa190534d022b78a40d'}
 canonical=bool(a.integration or a.exe)
 core=a.provider_core or ('temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a' if canonical else 'temp/provider-baseline08/libcorelib.a')
 allocator=a.provider_allocator or ('temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a' if canonical else 'temp/provider-baseline08/libpresonus_core_allocator.a')
 proof['provider_archives']={x:digest(R/x) for x in [core,allocator]}
 if a.integration:
  proof['integration_sha256']=digest(R/a.integration)
 proof['proposed_readiness']={'ready':[],'pending':[{'original_elf_sha256':native.SHA,'mangled':native.NAME,'original_address':native.ADDRESS,'sources':proof['sources'],'domain':proof['validation_domain'],'declaration_uncertainties':proof['limitations'],'repository_sources':proof['repository_sources'],'canonical_binding_pending':True}]}
 if a.out:Path(a.out).write_text(json.dumps(proof,indent=2)+'\n')
if __name__=='__main__':main()
