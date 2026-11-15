import argparse,hashlib,json,os,subprocess,sys,datetime
from pathlib import Path
R=Path(__file__).resolve().parents[4]; T=Path(__file__).resolve().parent
O=R/'temp/recovery-work/rolling10_replacement_spi_01';O.mkdir(parents=True,exist_ok=True)
OWNED=['uc-library/include/presonus/panel/GEQPage.hpp','uc-library/src/Presonus/Panel/GEQPage.cpp',str((T/'Replay.cpp').relative_to(R))]
FLAGS=['/usr/bin/c++','-std=c++17','-fno-rtti','-ffunction-sections','-fdata-sections','-Wno-multichar','-Iuc-library/include','-Ithird_party/ccl-framework']
ARCHIVES=[Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01')/n for n in ['libpresonus_uc.a','upstream-core/sdk/lib/libcorelib.a','upstream-core/sdk/lib/libpresonus_core_allocator.a']]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(a,**kw):
 print(json.dumps(list(map(str,a))),flush=True)
 p=subprocess.run(list(map(str,a)),cwd=R,capture_output=True,env={**os.environ,'TMPDIR':str(O)},**kw)
 if p.returncode: print(p.stdout.decode(),p.stderr.decode());p.check_returncode()
 return p.stdout.decode()
def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['format','compile','symbols','native','replay','proof']);p.add_argument('--exe');p.add_argument('--object');p.add_argument('--integration');p.add_argument('--out');a=p.parse_args()
 obj=Path(a.object) if a.object else O/'production.o';exe=Path(a.exe) if a.exe else O/'replay'
 if a.mode=='format':run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*OWNED]);return
 if a.mode=='compile':
  for source,target in [(OWNED[1],obj),(OWNED[2],O/'driver.o'),('uc-library/src/Presonus/Panel/GeqUIComponent.cpp',O/'group.o')]:run([*FLAGS,'-O2','-MMD','-MF',str(target)+'.d','-c',source,'-o',target])
  run(['/usr/bin/c++',obj,O/'driver.o',O/'group.o','-Wl,--gc-sections','-Wl,--wrap=_ZN8Presonus5Panel14GeqUIComponent17flattenCurrentGeqEv',*ARCHIVES,'-lz','-lpthread','-ldl','-lm','-o',exe]);return
 import native
 if a.mode=='native':assert native.generate()==json.loads((T/'fixtures.json').read_text());print('24 original ARM cases reproduced');return
 symbols=run(['nm','--defined-only',obj]);assert native.NAME in {s.split()[-1] for s in symbols.splitlines() if s.split()}
 if a.mode=='symbols':return
 fixture=json.loads((T/'fixtures.json').read_text());cases=fixture['cases']
 text=''.join(str(c['present'])+' '+str(c['selection'])+' '+str(c['count'])+'\n' for c in cases)
 lines=run([exe],input=text.encode()).splitlines();assert len(lines)==len(cases)
 for c,line in zip(cases,lines):assert list(map(int,line.split()))==[c['flatten_calls'],0,int(c['provider_entered'])],(c,line)
 print('24 recall/provider cases passed, borrowed binding and band retained')
 if a.mode=='replay':return
 assert a.out,'proof output required'
 files=set(OWNED)|{str((T/n).relative_to(R)) for n in ['check.py','native.py','fixtures.json']}
 for dep in O.glob('*.o.d'):
  files.update(x for x in dep.read_text().replace('\\\n',' ').split(':',1)[1].split() if (R/x).is_file())
 source_hash={f:sha(R/f) for f in sorted(files)}
 archive_hashes={str(x):sha(x) for x in ARCHIVES}
 limits=['Original ordinary return declaration unresolved; void is source-port choice.','Portable borrowed GeqUIComponent pointer; original offset 0x118, inheritance and ARM ABI unresolved.','Native executes original recall and exact existing-provider ARM range; deeper link/flatten calls excluded by null entries and zero Core error sentinel. Actual existing C++ GeqUIComponent executes with real pinned CCL Component; test dependency adapter supplies empty/null selection.','Bounded no-op selection domain only; populated GEQ components and link/slave/flatten side effects require further provider evidence. Caller owns both object lifetimes; no ownership transfer.']
 proof=dict(version=1,created=datetime.datetime.now(datetime.timezone.utc).isoformat(),task_id='rolling10_replacement_spi_01',session_id='/root/rolling10_spi',compiled=True,mangling_verified=True,formatting_verified=True,native_behavior_verified=True,behavior_verified=True,original_declaration_verified=False,original_arm_abi_verified=False,hardware_verified=False,canonical_binding_pending=a.integration is None,validation_domain=fixture['domain'],limitations=limits,range=fixture['ranges'][0],elf_sha256=native.SHA,source_sha256=source_hash,archive_sha256=archive_hashes,compiled_symbols=symbols,object_sha256=sha(obj),executable_sha256=sha(exe),fixture_sha256=sha(T/'fixtures.json'),formatter_version=run(['uc-library/.venv/bin/clang-format','--version']).strip(),compiler_version=run(['/usr/bin/c++','--version']).splitlines()[0],unicorn_version=__import__('unicorn').__version__,canonical_integration=dict(path=a.integration,sha256=sha(a.integration)) if a.integration else None)
 record=dict(elf_sha256=native.SHA,mangled=native.NAME,namespace='Presonus::Panel',validation_domain=fixture['domain'],declaration_uncertainties=limits[:2],source_sha256={k.removeprefix('uc-library/'):v for k,v in source_hash.items() if k in OWNED[:2]},repository_sources={k:v for k,v in source_hash.items() if k.startswith('third_party/')},canonical_binding_pending=True)
 proof['proposed_readiness']=dict(ready=[],pending=[record]);Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps(proof,indent=2)+'\n')
if __name__=='__main__':main()
