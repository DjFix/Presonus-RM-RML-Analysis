#!/usr/bin/env python3
import argparse,datetime,hashlib,json,os,shlex,subprocess,time
from pathlib import Path
import native
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent;TASK=T.name
P=Path('temp/recovery-work/rolling10x10-20261114/prepared-remaining14-phasea-proposed01/packets')/TASK
REQ=json.loads((R/P/'request.json').read_text());TARGET=REQ['targets'][0]
OWN=[x for x in REQ['owned_files'] if x.endswith(('.cpp','.hpp','.h'))]
WORK=R/'temp/recovery-work'/TASK;BUILD=Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01');SDK=BUILD/'upstream-core/sdk'
LIBS=[SDK/'lib/libcorelib.a',SDK/'lib/libpresonus_core_allocator.a',BUILD/'private-glibc29-provider/libpresonus_private_glibc29.a']
DOMAIN='1152 stable Numeric binding/value/repetition scenarios; 1536 exact original44-byte caller invocations, including both guard-null paths and restored-frame tail transfer to accepted updateHighDef. 384 zero-call scenarios check unchanged initial state. Two receiver identities, alias/nonalias source/destination, threshold neighbors, signed zero, finite values, infinities and NaN bits, initial destination values and0/1/3 calls. Original caller tail count drives independent direct accepted updateHighDef source/real CCL executions; compare value bits and all real controller/observer event order.'
LIMITS=['Original misspelled initalize name retained. void return is provisional; original static return, class layout/inheritance/ownership, ARM ABI and hardware remain unresolved.', 'Reuse accepted highDefSource_/highDefDestination_ and accepted updateHighDef implementation. No new state mirror, constructor or provider readiness credit. Stable actual NumericParam providers only; unknown overrides, reentrant retargeting and dangling references excluded.', 'Exact original caller only executes in native oracle. Its observed tail transfers invoke accepted source provider through an independent executable mode; no Core binary body or existing accepted app body is reconstructed. Source review establishes exactly one conditional production invocation; portable replay compares provider states/events rather than claiming instrumented call-count proof.', 'Actual CCL source canonicalizes initial signed zero and has NaN setter comparison behavior; fixture observations preserve actual provider results and notifications. No fresh original updateHighDef native helper equivalence is claimed.']
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
 f=json.loads((T/'fixtures.json').read_text());payload=''.join(' '.join(map(str,c['input']))+'\n' for c in f['cases']);out=run([exe],input=payload).splitlines();assert len(out)==len(f['cases'])
 for row,line in zip(f['cases'],out):assert list(map(int,line.split()))==row['accepted_provider_observation'],(row['input'],line,row['accepted_provider_observation'])
 return len(f['cases'])

def proof(a):
 version=fmt();s=symbols(a.object);f=native_check(a.exe);count=replay(a.exe)
 paths=set(OWN[:2]+[x for x in REQ.get('declared_source_dependencies',[]) if x.startswith('uc-library/')]);sources={p.removeprefix('uc-library/'):sha(R/p) for p in sorted(paths)}
 deps={p:sha(R/p) for p in REQ.get('declared_source_dependencies',[]) if p.startswith('third_party/ccl-framework/core/')}
 record=dict(original_elf_sha256=TARGET['original_elf_sha256'],mangled=TARGET['mangled'],demangled=run(['c++filt',TARGET['mangled']]).strip(),firmware=TARGET['firmware'],role=TARGET['role'],address=TARGET['address'],size=TARGET['size'],section=TARGET['section'],portable_ready=False,cpp_compiled=True,mangling_namespace_checked=True,validation_domain=DOMAIN,sources=sources,repository_sources=deps,declaration_uncertainties=LIMITS,original_function_verified=False,hardware_verified=False)
 proof=dict(task_id=TASK,worker_session='/root/rolling10_fx',timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),native=f,sources=sources,repository_sources=deps,cpp_differential_passed=True,compiled_original_mangled_names_matched=True,compiled_symbols=s,portable_case_count=count,formatting=dict(version=version,passed=True,sources=sources),validation_domain=DOMAIN,limitations=LIMITS,canonical_binding_pending=not bool(a.integration),proposed_readiness=dict(ready=[],pending=[record]),binary_bindings={str(a.exe):sha(a.exe),str(a.object):sha(a.object)},provider_libraries={str(p):sha(p) for p in LIBS},fixture_sha256=sha(T/'fixtures.json'),producer_sha256=sha(__file__),test_sources={str(T.relative_to(R)/'Replay.cpp'):sha(T/'Replay.cpp')})
 proof['native_invocations']=sum(c['input'][4] for c in f['cases'])
 proof['baseline_bindings']={'uc-library/include/presonus/mixer/GlobalComponent.hpp':'f3108c115436454de3b966526cd22468fee48a5a9b53e11ffe2b4f6ba6a008b2','uc-library/src/Presonus/Mixer/GlobalComponent.cpp':'1446e369fbe7c4cf51c669ef9ca0bdb7d3bfacec53af976286cc922aab68b6c5'}
 proof['accepted_provider_binding']=REQ['reconstruction_contract']
 # Accepted provider source is frozen baseline evidence, not a regenerated old proof.
 readmap=R/'temp/recovery-work/rolling10x10-20261114/READ_INPUTS-prepared-remaining14-phasea-proposed01-rolling10_fx.json'
 baseline=Path(json.loads(readmap.read_text())['uc-library/src/Presonus/Mixer/GlobalComponent.cpp']['frozen_read_path'])
 assert sha(baseline)=='1446e369fbe7c4cf51c669ef9ca0bdb7d3bfacec53af976286cc922aab68b6c5'
 def function_body(text,name):
  start=text.index(name);a=text.index('{',start);depth=1;b=a+1
  while depth:
   depth+=(text[b]=='{')-(text[b]=='}');b+=1
  return ''.join(text[start:b].split())
 current=(R/'uc-library/src/Presonus/Mixer/GlobalComponent.cpp').read_text();old=baseline.read_text()
 for name in ['void GlobalComponent::updateHighDef()','GlobalComponent::getTempFilePath()']:
  assert function_body(current,name)==function_body(old,name), 'Accepted provider/legacy body changed'
 proof['accepted_source_preservation']={'baseline':str(baseline),'sha256':sha(baseline),'functions_token_preserved':['updateHighDef','getTempFilePath'],'scope':'Source-body preservation only; original return/layout and provider readiness limitations retained.'}

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
