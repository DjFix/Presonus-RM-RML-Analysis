#!/usr/bin/env python3
import argparse,datetime,hashlib,json,os,shlex,subprocess,time
from pathlib import Path
import native
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent;TASK=T.name
P=Path('temp/recovery-work/rolling10x10-20261114/prepared06/packets')/TASK
REQ=json.loads((R/P/'request.json').read_text());TARGET=REQ['targets'][0]
OWN=[x for x in REQ['owned_files'] if x.endswith(('.cpp','.hpp','.h'))]
WORK=R/'temp/recovery-work'/TASK;BUILD=Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01');SDK=BUILD/'upstream-core/sdk'
LIBS=[SDK/'lib/libcorelib.a',SDK/'lib/libpresonus_core_allocator.a',BUILD/'private-glibc29-provider/libpresonus_private_glibc29.a']
DOMAIN='Eight independent native cases: empty, custom/unselected, unchanged chN, reordered names, mixed prefix/nonprefix/case-sensitive names, 31-byte names, duplicate names and zero/multiple parameters. Real CCL CString32 formatting, Vector membership and Parameter::changed observer snapshots service only original Core boundaries; libc string calls use host libc. All selected names change before any observer; parameter order/snapshots and borrowed child identities compared to C++.'
LIMITS=['Original ordinary return, inheritance/layout and ARM ABI unresolved. void return is a portable choice. No hardware validation.','Native Core methods are not executed; explicit memory adapters transport actual pinned CCL provider observations. Host libc source behavior is the provider model, not old glibc binary equivalence.','Valid nonnull stable child/parameter objects and successful allocation only. Reentrant observers, allocation failure and native exception cleanup not covered; no original constructor/destructor credit.']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(argv,input=None):
 argv=list(map(str,argv));stamp=datetime.datetime.now(datetime.timezone.utc).isoformat();start=time.monotonic();r=subprocess.run(argv,cwd=R,input=input,text=True,capture_output=True,env={**os.environ,'TMPDIR':str(WORK)})
 with (WORK/'commands.jsonl').open('a') as f:f.write(json.dumps(dict(start_utc=stamp,end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),seconds=time.monotonic()-start,argv=argv,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))+'\n')
 if r.returncode:print(r.stdout,r.stderr);r.check_returncode()
 return r.stdout

def fmt():
 v=run(['uc-library/.venv/bin/clang-format','--version']).strip();run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*OWN]);return v

def compile():
 flags=['/usr/bin/c++','-std=c++17','-O2','-fno-rtti','-fno-lto','-Wno-multichar','-ffunction-sections','-fdata-sections','-Ulinux','-pthread','-Iuc-library/include','-Ithird_party/ccl-framework']
 production=[x for x in OWN if '/src/' in x];driver=next(x for x in OWN if '/tests/' in x)
 assert len(production)==1
 run(flags+['-c',production[0],'-o',WORK/'production.o']);run(flags+['-c',driver,'-o',WORK/'driver.o'])
 run(['/usr/bin/c++',WORK/'production.o',WORK/'driver.o','-Wl,--gc-sections','-Wl,--start-group',*LIBS,'-Wl,--end-group','-pthread','-ldl','-lm','-lz','-o',WORK/'replay'])

def symbols(obj):
 s=run(['nm','--defined-only',obj]);assert TARGET['mangled'] in [r.split()[-1] for r in s.splitlines() if r.split()];return s

def native_check(exe):
 f=native.generate(exe.resolve());assert f==json.loads((T/'fixtures.json').read_text());return f

def replay(exe):
 f=json.loads((T/'fixtures.json').read_text())
 for c in f['cases']:
  payload=str(len(c['input']))+'\n'+''.join(json.dumps(n)+' '+str(k)+'\n' for n,k in c['input'])
  out=run([exe],input=payload).splitlines();assert shlex.split(out[0])==[str(len(c['names'])),*c['names']];assert int(out[1])==len(c['events']);assert out[2:]==c['events']
 return len(f['cases'])

def proof(a):
 version=fmt();s=symbols(a.object);f=native_check(a.exe);count=replay(a.exe)
 paths=set(OWN[:2]+[x for x in REQ.get('declared_source_dependencies',[]) if x.startswith('uc-library/')]);sources={p.removeprefix('uc-library/'):sha(R/p) for p in sorted(paths)}
 deps={p:sha(R/p) for p in REQ.get('declared_source_dependencies',[]) if p.startswith('third_party/ccl-framework/core/')}
 record=dict(original_elf_sha256=TARGET['original_elf_sha256'],mangled=TARGET['mangled'],demangled=run(['c++filt',TARGET['mangled']]).strip(),firmware=TARGET['firmware'],role=TARGET['role'],address=TARGET['address'],size=TARGET['size'],section=TARGET['section'],portable_ready=False,cpp_compiled=True,mangling_namespace_checked=True,validation_domain=DOMAIN,sources=sources,repository_sources=deps,declaration_uncertainties=LIMITS,original_function_verified=False,hardware_verified=False)
 proof=dict(task_id=TASK,worker_session='/root/rolling10_fx',timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),native=f,sources=sources,repository_sources=deps,cpp_differential_passed=True,compiled_original_mangled_names_matched=True,compiled_symbols=s,portable_case_count=count,formatting=dict(version=version,passed=True,sources=sources),validation_domain=DOMAIN,limitations=LIMITS,canonical_binding_pending=not bool(a.integration),proposed_readiness=dict(ready=[],pending=[record]),binary_bindings={str(a.exe):sha(a.exe),str(a.object):sha(a.object)},provider_libraries={str(p):sha(p) for p in LIBS},fixture_sha256=sha(T/'fixtures.json'),producer_sha256=sha(__file__),test_sources={str(T.relative_to(R)/'Replay.cpp'):sha(T/'Replay.cpp')})
 if a.integration:proof['integration']={'path':str(a.integration),'sha256':sha(a.integration)}
 out=a.out or R/'uc-library/candidates'/TASK/'worker-proof.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(proof,indent=2)+'\n');print(out)

def main():
 p=argparse.ArgumentParser();p.add_argument('mode',nargs='?',default='proof',choices=['format','compile','symbols','native','replay','proof']);p.add_argument('--exe',type=Path,default=WORK/'replay');p.add_argument('--object',type=Path,default=WORK/'production.o');p.add_argument('--integration',type=Path);p.add_argument('--out',type=Path);a=p.parse_args();WORK.mkdir(parents=True,exist_ok=True)
 if a.mode=='format':print(fmt())
 elif a.mode=='compile':compile()
 elif a.mode=='symbols':print(symbols(a.object))
 elif a.mode=='native':print(len(native_check(a.exe)['cases']),'original app/provider cases')
 elif a.mode=='replay':print(replay(a.exe),'differential cases')
 else:proof(a)
if __name__=='__main__':main()
