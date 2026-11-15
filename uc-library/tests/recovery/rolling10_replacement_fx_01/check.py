#!/usr/bin/env python3
"""Bounded original ARM versus compiled port; explicit canonical input binding."""
import argparse,datetime,hashlib,json,os,shlex,subprocess,time
from pathlib import Path
T=Path(__file__).resolve().parent;R=T.parents[3];TASK=T.name
P=Path('temp/recovery-work/rolling10x10-20261114/prepared05/packets')/TASK
REQUEST=json.loads((R/P/'request.json').read_text());TARGET=REQUEST['targets'][0]
CLASSES={'rolling10_fx_01':'FXComponent','rolling10_fx_02':'GambitMixerComponent','rolling10_fx_03':'ReverbComponent','rolling10_replacement_fx_01':'GambitRMLApplication','rolling10_replacement_fx_02':'WolverineRMLApplication'}
CLASS=CLASSES[TASK]
SOURCES=[f'uc-library/include/presonus/mixer/{CLASS}.hpp',f'uc-library/src/Presonus/Mixer/{CLASS}.cpp',str((T/'Replay.cpp').relative_to(R))]
WORK=R/'temp/recovery-work'/TASK
CANONICAL=Path('/home/rs/projects/opencs/ai-line-analysis');BUILD=CANONICAL/'temp/core-upstream/root-integration-01';SDK=BUILD/'upstream-core/sdk'
DOMAIN='Exact original app body under ARM Unicorn; valid isolated caller memory, two self addresses, boundary/seeded enum bits or eight sentinel patterns. Native instruction PCs, stack writes, output writes, no external execution and unchanged caller bytes recorded. Compiled portable replay compares identity bits/count, complete 24-row table with relocated strings, or network port/name/GUID with all other canonical ServerInfo members and borrowed string memory preserved. No lifecycle or hardware recovery claim.'
LIMITATIONS=['Original ordinary return declarations remain unresolved; matching mangling does not prove return types, original inheritance/layout/ownership or ARM ABI.','Only valid disjoint caller references tested for network methods; overlapping, dangling and null references excluded from the portable domain. Network void return is a source-port choice; native r0 remains the input self address.','Reverb row type and const pointer return are provisional; native table addresses are normalized through a static portable table, not numeric pointer equality.','FX uses actual CCL objects and existing authoritative state; provider behavior is source based. Native app body calls no external provider. Constructors/destructors of original app classes are not reconstructed.','No hardware, device update or flashing operations.']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rel(p):return str(Path(p).relative_to(R))
def run(argv,input=None):
 argv=list(map(str,argv));start=time.monotonic();r=subprocess.run(argv,cwd=R,input=input,text=True,capture_output=True,env={**os.environ,'TMPDIR':str(WORK)})
 row=dict(start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),argv=argv,seconds=time.monotonic()-start,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)
 with (WORK/'commands.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
 if r.returncode: print(r.stdout,r.stderr);r.check_returncode()
 return r.stdout

def format_check():
 version=run(['uc-library/.venv/bin/clang-format','--version']).strip()
 run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*SOURCES]);return version

def compile_check():
 flags=['/usr/bin/c++','-std=c++17','-O2','-fno-rtti','-fno-lto','-Wno-multichar','-ffunction-sections','-fdata-sections','-UNDEBUG','-Ulinux','-pthread','-Iuc-library/include','-Ithird_party/ccl-framework']
 run(flags+['-c',SOURCES[1],'-o',WORK/'production.o']);run(flags+['-c',SOURCES[2],'-o',WORK/'driver.o'])
 libs=[]
 if TASK=='rolling10_fx_01':libs=['-Wl,--start-group',SDK/'lib/libcorelib.a',SDK/'lib/libpresonus_core_allocator.a',BUILD/'private-glibc29-provider/libpresonus_private_glibc29.a','-Wl,--end-group','-pthread','-ldl','-lm','-lz']
 run(['/usr/bin/c++',WORK/'production.o',WORK/'driver.o','-Wl,--gc-sections',*libs,'-o',WORK/'replay'])

def symbols(obj):
 out=run(['/usr/bin/nm','--defined-only',obj]);assert TARGET['mangled'] in [line.split()[-1] for line in out.splitlines() if line.split()];return out

def native_check():
 import native
 current=native.generate();bound=json.loads((T/'fixtures.json').read_text());assert current==bound,'fresh native observations differ from bound fixtures';return current

def replay(exe):
 f=json.loads((T/'fixtures.json').read_text());kind=f['kind'];case=f['cases'];payload=''.join(str(c['input'][1])+'\n' for c in case)
 actual=run([exe],input=payload).splitlines()
 if kind=='table':
  expected=[[str(r['family']),str(r['index']),str(r['effect_bits']),str(r['value_bits']),r['name']] for r in f['table']]
  got=[shlex.split(line) for line in actual];assert got==expected,(got,expected);return len(expected)
 elif kind=='network':
  expected=[[str(c['expected']['port']),c['expected']['name'],c['expected']['guid']] for c in case]
  assert [shlex.split(line) for line in actual]==expected
 else:assert actual==[str(c['r0']) for c in case],(actual,case)
 return len(case)

def proof(a):
 formatter=format_check();f=native_check();nm=symbols(a.object);count=replay(a.exe)
 srcs={s.removeprefix('uc-library/'):sha(R/s) for s in SOURCES[:2]}
 dependencies=[]
 if TASK=='rolling10_fx_01':dependencies=['third_party/ccl-framework/core/portable/corecomponent.h','third_party/ccl-framework/core/portable/corecomponent.cpp','third_party/ccl-framework/core/portable/coreparams.h','third_party/ccl-framework/core/portable/coreparams.cpp','third_party/ccl-framework/core/public/coretypes.h']
 if TASK=='rolling10_fx_01':srcs['include/presonus/mixer/DelayComponent.hpp']=sha(R/'uc-library/include/presonus/mixer/DelayComponent.hpp')
 if 'replacement' in TASK:srcs['include/presonus/uc/server_registrar.hpp']=sha(R/'uc-library/include/presonus/uc/server_registrar.hpp');dependencies=['third_party/ccl-framework/core/public/corevector.h']
 deps={s:sha(R/s) for s in dependencies}
 entry=dict(original_elf_sha256=TARGET['original_elf_sha256'],mangled=TARGET['mangled'],demangled=run(['/usr/bin/c++filt',TARGET['mangled']]).strip(),firmware=TARGET.get('firmware','RM/RML mixer 13731'),role='server',address=TARGET['address'],size=TARGET['size'],section=TARGET['section'],portable_ready=False,cpp_compiled=True,mangling_namespace_checked=True,original_function_verified=False,hardware_verified=False,sources=srcs,repository_sources=deps,validation_domain=DOMAIN,declaration_uncertainties=LIMITATIONS)
 canonical=bool(a.integration)
 result=dict(version=1,task_id=TASK,worker_session='/root/rolling10_fx',timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),platform='Linux',native=f,portable_case_count=count,sources=srcs,repository_sources=deps,cpp_differential_passed=True,compiled_original_mangled_names_matched=True,mangling_namespace_checked=True,portable_ready=False,hardware_verified=False,original_function_verified=False,formatting=dict(version=formatter,source_hashes=srcs,passed=True),validation_domain=DOMAIN,limitations=LIMITATIONS,canonical_binding_pending=not canonical,proposed_readiness=dict(ready=[],pending=[entry]),binary_bindings={str(a.exe):sha(a.exe),str(a.object):sha(a.object)},fixture_sha256=sha(T/'fixtures.json'),producer_sha256=sha(__file__),commands_log=rel(WORK/'commands.jsonl'))
 result['compiled_symbols']=nm
 result['test_sources']={SOURCES[2]:sha(R/SOURCES[2])}
 if canonical:result['integration']={'path':str(a.integration),'sha256':sha(a.integration)}
 if TASK=='rolling10_fx_01':result['linked_providers']={str(x):sha(x) for x in [SDK/'lib/libcorelib.a',SDK/'lib/libpresonus_core_allocator.a',BUILD/'private-glibc29-provider/libpresonus_private_glibc29.a']}
 out=a.out or R/'uc-library/candidates'/TASK/'worker-proof.json'
 if out.suffix!='.json':out=out/'worker-proof.json'
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n');print(out)

def main():
 p=argparse.ArgumentParser();p.add_argument('mode',nargs='?',default='proof',choices=['format','compile','symbols','native','replay','proof']);p.add_argument('--exe',type=Path,default=WORK/'replay');p.add_argument('--object',type=Path,default=WORK/'production.o');p.add_argument('--integration',type=Path);p.add_argument('--out',type=Path);a=p.parse_args();WORK.mkdir(parents=True,exist_ok=True)
 if a.mode=='format':print(format_check())
 elif a.mode=='compile':compile_check()
 elif a.mode=='symbols':print(symbols(a.object))
 elif a.mode=='native':print('Original executions:',len(native_check()['cases']))
 elif a.mode=='replay':print('Compiled differential comparisons:',replay(a.exe))
 else:proof(a)
if __name__=='__main__':main()
