import argparse,json,hashlib,subprocess,os,sys,datetime
from pathlib import Path
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent
CONFIG={'name': 'rolling10_next100_gate_keylisten', 'header': 'uc-library/include/presonus/surface/GatePageComponent.hpp', 'source': 'uc-library/src/Presonus/Surface/GatePageComponent.cpp', 'namespace': 'Presonus::Surface', 'domain': '16 exact original ARM cases: missing/present key, false/true, initial -1/0/0.5/1; exact literal and virtual dispatch slots verified; actual pinned Component lookup/NumericParam setValue(true) independently executed, value/changed notifications and unrelated parameter compared.', 'limits': ['Original void return and original inheritance/layout/ARM ABI unresolved; actual CCL Component base is intentional source port.', 'Native Core bodies never execute; exact inherited findParameter and NumericParam slots are translated to independently executed actual pinned source provider, recording arguments and notifications. Only valid actual NumericParam receiver domain supported; other subclasses excluded.', 'Metadata outlives owning Component registry with ownsInfo=false; actual CCL destruction retained, no original lifecycle credit.'], 'archives': True, 'started': '2026-11-14T05:44:01.881940+00:00'}
O=R/'temp/recovery-work'/CONFIG['name'];O.mkdir(parents=True,exist_ok=True)
SOURCES=[CONFIG['source'],str((T/'Replay.cpp').relative_to(R))]
OWNED=[CONFIG['header'],*SOURCES]
FLAGS=['/usr/bin/c++','-std=c++17','-O2','-fno-rtti','-ffunction-sections','-fdata-sections','-Wno-multichar','-Iuc-library/include','-Ithird_party/ccl-framework']
SDK=Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk/lib')
ARCHIVES=[SDK/'libcorelib.a',SDK/'libpresonus_core_allocator.a'] if CONFIG['archives'] else []
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(argv,**kw):
 print(json.dumps(list(map(str,argv))),flush=True)
 p=subprocess.run(list(map(str,argv)),cwd=R,capture_output=True,env={**os.environ,'TMPDIR':str(O)},**kw)
 if p.returncode: print(p.stdout.decode(),p.stderr.decode());p.check_returncode()
 return p.stdout.decode()
def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['format','compile','symbols','native','replay','proof']);p.add_argument('--exe');p.add_argument('--object');p.add_argument('--integration');p.add_argument('--out');a=p.parse_args()
 obj=Path(a.object) if a.object else O/'production.o';exe=Path(a.exe) if a.exe else O/'replay'
 if a.mode=='format':run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*OWNED]);return
 if a.mode=='compile':
  for source,target in zip(SOURCES,[obj,O/'driver.o']):run([*FLAGS,'-MMD','-MF',str(target)+'.d','-c',source,'-o',target])
  run(['/usr/bin/c++',obj,O/'driver.o','-Wl,--gc-sections',*ARCHIVES,'-lz','-lpthread','-ldl','-lm','-o',exe]);return
 import native
 fixture=json.loads((T/'fixtures.json').read_text())
 if hasattr(native,'EXE'):native.EXE=exe
 fresh_native = native.generate() if a.mode in ['native','proof'] else None
 if fresh_native is not None:assert fresh_native==fixture
 if a.mode=='native':print('fresh original observations reproduce fixture');return
 symbols=run(['nm','--defined-only',obj]);assert native.NAME in {x.split()[-1] for x in symbols.splitlines() if x.split()}
 if a.mode=='symbols':return
 lines=run([exe],input=''.join(c['stdin']+'\n' for c in fixture['cases']).encode()).splitlines();assert lines==[c['stdout'] for c in fixture['cases']],(lines[:5],fixture['cases'][:5])
 print(len(lines),'native/provider differential cases pass')
 if a.mode=='replay':return
 assert a.out
 files=set(OWNED)|{str((T/n).relative_to(R)) for n in ['native.py','check.py','fixtures.json']}
 for dep in O.glob('*.o.d'):
  files.update(x for x in dep.read_text().replace('\\\n',' ').split(':',1)[1].split() if (R/x).is_file())
 hashes={f:sha(R/f) for f in sorted(files)}
 pending=dict(original_elf_sha256=native.SHA,mangled=native.NAME,portable_ready=False,cpp_compiled=True,mangling_namespace_checked=True,sources={k.removeprefix('uc-library/'):v for k,v in hashes.items() if k.startswith('uc-library/') and not k.startswith('uc-library/tests/')},repository_sources={k:v for k,v in hashes.items() if k.startswith('third_party/ccl-framework/core/')},domain=CONFIG['domain'],declaration_uncertainties=CONFIG['limits'],canonical_binding_pending=True)
 proof=dict(version=1,created=datetime.datetime.now(datetime.timezone.utc).isoformat(),session_id='/root/rolling10_spi',phase_timestamps=dict(reconstruction_start=CONFIG['started'],validation_end=datetime.datetime.now(datetime.timezone.utc).isoformat()),task_id=CONFIG['name'],compiled=True,formatting_verified=True,mangling_verified=True,behavior_verified=True,native_behavior_verified=True,original_declaration_verified=False,original_arm_abi_verified=False,hardware_verified=False,canonical_binding_pending=True,validation_domain=CONFIG['domain'],limitations=CONFIG['limits'],ranges=fixture['ranges'],elf_sha256=native.SHA,source_sha256=hashes,archive_sha256={str(x):sha(x) for x in ARCHIVES},compiled_symbols=symbols,object_sha256=sha(obj),executable_sha256=sha(exe),formatter_version=run(['uc-library/.venv/bin/clang-format','--version']).strip(),compiler_version=run(['/usr/bin/c++','--version']).splitlines()[0],proposed_readiness=dict(ready=[],pending=[pending]),integration=dict(path=a.integration,sha256=sha(a.integration)) if a.integration else None)
 proof['fresh_native_execution'] = dict(elf_sha256=fresh_native['elf_sha256'],ranges=fresh_native['ranges'],case_count=len(fresh_native['cases']),observations_sha256=hashlib.sha256(json.dumps(fresh_native,sort_keys=True).encode()).hexdigest(),producer_sha256=sha(T/'native.py'),unicorn_version=__import__('unicorn').__version__,executed_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
 supplement=R/'temp/recovery-work/spi-generation06/supplemental-bindings.json'
 binding=json.loads(supplement.read_text())['deliveries'][CONFIG['name']]
 for path,digest in binding['typed_contract_and_evidence'].items():assert sha(path)==digest
 for path,digest in binding['provider_repository_sources'].items():
  assert sha(path)==digest
  proof['source_sha256'][path]=digest
  proof['proposed_readiness']['pending'][0]['repository_sources'][path]=digest
 proof['supplemental_evidence']=dict(path=str(supplement.relative_to(R)),sha256=sha(supplement))
 proof['typed_contract_and_evidence']=binding['typed_contract_and_evidence']
 Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps(proof,indent=2)+'\n')
if __name__=='__main__':main()
