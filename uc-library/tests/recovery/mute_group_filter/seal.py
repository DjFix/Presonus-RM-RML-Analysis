"""Seal both exact packet deliveries after final shared-source checks."""
import json,hashlib,subprocess,datetime,os,time
from pathlib import Path
R=Path(__file__).resolve().parents[4];T=Path('uc-library/tests/recovery/mute_group_filter');E=Path('evidence/recovery/2026-11-06/rolling200-02/mute-filters98');PY='uc-library/.venv/bin/python'
E.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
checks=[dict(kind=k,argv=[PY,str(T/'check.py'),k],timeout_seconds=240) for k in ['format','compile','symbols','native','replay']]
logs=[]
for c in checks:
 start=time.time();p=subprocess.run(c['argv'],text=True,capture_output=True,timeout=240);f=E/(c['kind']+'.log');f.write_text(p.stdout+p.stderr);logs.append(dict(**c,returncode=p.returncode,seconds=time.time()-start,log=str(f),sha256=sha(f)));print(c['kind'],p.returncode,flush=True);assert not p.returncode,p.stdout+p.stderr
limits=['Portable source port only: original return declarations, inheritance, layout, ARM ABI and hardware remain unresolved. bool overrides actual pinned CCL interface; matching ELF names do not verify original return.', 'Native test object/vtable/string memory is explicit oracle-only boundary modeling. strcmp, virtual getValue and __aeabi_fcmpeq are intercepted before provider execution; all target instructions run from full hash-verified original ranges. No guest Core or hardware/system calls.', 'CCL ParamInfo embeds a fixed char name array, so native null-name fallback is deliberately projected to empty CCL name. Production uses actual provider representation, not ARM offsets. Component/Parameter type IDs observed equal native literals.', 'Valid borrowed Parameter object required for Para; other types and null Para never dereference. Parameter override returns supplied IEEE float including signed zero, infinities, quiet NaNs and subnormals. No invalid pointers, signaling NaN traps, concurrency or allocator failure claim.', 'Existing MuteGroupBase state/lifecycle unchanged; base activate and FileMuteGroup/Storm targets remain separately owned. Root canonical integration and guarded admission remain pending.']
domain='2240 exact original ARM executions and actual pinned CCL differential cases: both methods; Comp/Para/0/-1 type IDs; null/present object; mute/Mute/empty/muted/space-prefix/prefix/null-native-name; +/-zero, +/-one, +/-infinity, +/-quiet-NaN and +/-subnormal; null/non-null ignored name argument. Capture original calls/PCs/stack stores and verify virtual getValue short-circuit counts.'
files={'uc-library/include/presonus/MuteGroupBase.hpp','uc-library/src/Presonus/MuteGroupFilter.cpp','uc-library/tests/recovery/MuteGroupFilterReplay.cpp','AGENTS.md','docs/worker-handoff.md','docs/core-framework-lineage.md'}
files.update(str(p) for p in T.glob('*') if p.is_file());files.update(str(p) for p in E.glob('*') if p.is_file() and p.name!='proof.json')
for p in ['core/portable/coreparams.h','core/portable/coreparams.cpp','core/portable/coreparaminfo.h','core/portable/corestorage.h','core/portable/corecomponent.h','core/portable/coretypeinfo.h']:files.add('third_party/ccl-framework/'+p)
for p in ['libcorelib.a','libpresonus_core_allocator.a']:files.add('temp/core-upstream/root-integration-01/upstream-core/sdk/lib/'+p)
versions={}
for key,cmd in [('clang-format',['uc-library/.venv/bin/clang-format','--version']),('compiler',['/usr/bin/c++','--version']),('nm',['nm','--version']),('ccl',['git','-C','third_party/ccl-framework','log','--reverse','--format=%H %P']),('oracle',[PY,'-c','import unicorn,elftools;print(unicorn.__version__,elftools.__version__)'])]:versions[key]=subprocess.check_output(cmd,text=True).strip()
assert versions['ccl'].splitlines()[0].strip()=='e8cbdea4a4a20e15111f5a690798a259c0374b31'
for i in [1,2]:
 packet=Path('temp/recovery-work/rolling200-02/next-implementation98/prepared-mute-filters98/packets')/f'rolling200_02_mute_filters98_0{i}';files.update(str(p) for p in packet.glob('*') if p.is_file())
notes=dict(date=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='local validated compiled-declaration-pending; Root admission pending',remarks=limits,retry_condition='Original return/inheritance declaration evidence plus canonical integration gates for promotion',originals=json.loads((T/'fixtures.json').read_text())['ranges']);(E/'NOTES.json').write_text(json.dumps(notes,indent=2)+'\n');files.add(str(E/'NOTES.json'))
proof=dict(version=1,cwd=str(R),base_commit='6c6bbb7a09708a4acae05884cbc2e34726e6baff',session_id=os.environ.get('CODEX_THREAD_ID'),versions=versions,commands=logs,original_elf_sha256=json.loads((T/'fixtures.json').read_text())['elf_sha256'],ranges=notes['originals'],source_sha256={p:sha(p) for p in sorted(files)},validation_domain=domain,limitations=limits,formatting_verified=True,compiled=True,mangling_verified=True,namespace_signature_verified=True,native_behavior_verified=True,original_declaration_verified=False,original_arm_abi_verified=False,hardware_verified=False)
(E/'proof.json').write_text(json.dumps(proof,indent=2)+'\n');files.add(str(E/'proof.json'))
for i in [1,2]:
 task=f'rolling200_02_mute_filters98_0{i}';packet=Path('temp/recovery-work/rolling200-02/next-implementation98/prepared-mute-filters98/packets')/task;req=json.loads((packet/'request.json').read_text());o=req['originals'][0]['original'];out=Path('uc-library/candidates')/task;out.mkdir(parents=True,exist_ok=True)
 def kind(p):
  if p==str(packet/'context.json'):return 'packet'
  if p==str(E/'proof.json'):return 'proof'
  if p==str(T/'fixtures.json'):return 'fixture'
  if p==str(T/'check.py'):return 'replay'
  if p.startswith('uc-library/src/') or p.startswith('uc-library/include/'):return 'source'
  if p.endswith('.cpp'):return 'test'
  return 'dependency'
 handoff=dict(version=1,task_id=task,namespace='Presonus',packet_manifest=str(packet/'context.json'),originals=[dict(elf_sha256=o['elf'],firmware=o['firmware'],role=o['role'],mangled=o['mangled'],address=o['address'],size=o['size'],section='.text')],artifacts=[dict(kind=kind(p),path=p,sha256=sha(p)) for p in sorted(files)],checks=checks,validation_domain=domain,limitations=limits,build_integration=dict(production_partition='common OBJECT: src/Presonus/MuteGroupFilter.cpp exactly once; original RM symbols, shared FileMute/Storm provider responsibility',public_headers=['include/presonus/MuteGroupBase.hpp'],test_targets=['MuteGroupFilterReplay'],test_sources=['tests/recovery/MuteGroupFilterReplay.cpp'],link_dependencies=['actual pinned corelib','presonus_core_allocator','png','zlib','pthread','dl','m'],ctest_argv=[PY,str(T/'check.py'),'replay','<canonical-built-MuteGroupFilterReplay>',str(T/'fixtures.json')],fixture_sha256=sha(T/'fixtures.json')))
 (out/'HANDOFF.json').write_text(json.dumps(handoff,indent=2)+'\n')
print('Both HANDOFF v1 sealed')
