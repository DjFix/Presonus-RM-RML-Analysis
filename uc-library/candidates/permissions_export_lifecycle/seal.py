#!/usr/bin/env python3
"""Seal completed bounded worker validation, without global readiness admission."""
import datetime,hashlib,json,shutil,subprocess
from pathlib import Path
BASE=Path('uc-library/candidates/permissions_export_lifecycle')
WORK=Path('temp/recovery-work/permissions-export-lifecycle-local01')
EV=Path('evidence/recovery/2026-11-05/permissions-export-lifecycle01')
PACKETS=Path('temp/recovery-work/rolling200-02/next-implementation08/prepared09-permissions_lifecycle08/packets')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def artifact(p,kind):return dict(path=str(p),kind=kind,sha256=sha(p))
def main():
 EV.mkdir(parents=True,exist_ok=True)
 for n in ['commands.jsonl','format.log','compile.log','symbols.log','native.log','replay.log','sanitizers.log']:
  shutil.copyfile(WORK/n,EV/n)
 for n in ['native.log','replay.log','sanitizers.log']:
  assert 'Traceback' not in (EV/n).read_text()
 assert 'Passed 1110' in (EV/'replay.log').read_text() and 'Passed 1110' in (EV/'sanitizers.log').read_text()
 native=json.loads((EV/'native-proof.json').read_text())
 rows=json.loads((EV/'native-fixtures.json').read_text())['cases']
 # The copied suffix is demonstrably entry-stack-dependent, not a fixed value.
 by={}
 for r in rows:
  c=r['input']
  if c['op']==0:by.setdefault((c['mix'],c['other']),set()).add(r['observed']['suffix'])
 assert all(len(v)==3 for v in by.values())
 sources=['uc-library/include/presonus/mixer/PermissionsComponent.hpp','uc-library/src/Presonus/Mixer/PermissionsComponent.cpp','uc-library/tests/recovery/PermissionsExportLifecycleReplay.cpp','uc-library/candidates/permissions_export_lifecycle/header_consumer.cpp']
 dependencies=['uc-library/include/presonus/uc/ClientSubscription.hpp','uc-library/include/presonus/uc/ServerComponent.hpp','uc-library/src/Presonus/UC/ServerComponent.cpp','third_party/ccl-framework/core/public/corestringbuffer.h','third_party/ccl-framework/core/public/corevector.h','third_party/ccl-framework/core/portable/corecomponent.h','third_party/ccl-framework/core/portable/corecomponent.cpp','third_party/ccl-framework/core/portable/coreparams.h','third_party/ccl-framework/core/portable/coreparams.cpp','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a','temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a','temp/core-upstream/root-integration-01/libpresonus_rm_components.a']
 artifacts=[artifact(p,'test' if p.endswith('Replay.cpp') or p.endswith('header_consumer.cpp') else 'source') for p in sources]+[artifact(p,'dependency') for p in dependencies]+[artifact(BASE/n,'replay' if n=='checks.py' else 'producer') for n in ['native_oracle.py','checks.py','seal.py']]
 artifacts += [artifact(p,'fixture' if p.name=='native-fixtures.json' else 'proof') for p in sorted(EV.iterdir()) if p.is_file() and p.name not in ['local-proof.json','REMARKS.json']]
 limitations=['Portable source port only; original return type, member layout, ARM32 ABI and hardware interoperability unresolved. exportClient provisional unsigned char* remains declaration-pending.', 'Only deterministic first 12 exported bytes and output identity compared. Native suffix bytes 12..74 vary with entry stack; source port intentionally zeroes all 63, not native-equivalent.', 'Core firmware bodies never executed. Native named CCL/libc dependencies use explicit semantic boundary hooks; compiled replay uses actual pinned CCL5.0.0 and host C++/libc.', 'Normal nonthrowing destructor domain only. Original EH cleanup at ServerComponent and __cxa_end_cleanup excluded; not a second normal base destruction.', 'Native-equivalence selected domain requires null or portableOwnSelected-owned snapshot. Legacy constructor still borrows arbitrary external snapshots and is independently checked not to delete them.', 'Original PermissionsComponent and ClientSubscription constructors not recovered or credited; independent owned setup copies only existing partial app/device/display values. Vector borrows pointees.', 'D1/D2 host replay directly executes exact compiled base destructor entry, excludes derived body, then releases raw storage outside observation. D0 deletes through actual CCL virtual base, observing derived destructor and actual host object deallocation.']
 proof=dict(version=1,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),worker='rolling200_02_permissions_export_lifecycle',checkout=str(Path.cwd()),baseline='95e1a9fc26b3d6909f272c1618ad842bb8c878b5',original_ranges=native['ranges'],native_cases=1110,portable_cases=1110,sanitizer_cases=1110,native_export_cases=1098,native_lifecycle_cases=12,provider_commit='e8cbdea4a4a20e15111f5a690798a259c0374b31',provider_root_commit_verified=True,formatter=subprocess.check_output(['uc-library/.venv/bin/clang-format','--version'],text=True).strip(),commands_log=str(EV/'commands.jsonl'),native_execution='Only assigned four ARM app bodies in Unicorn guarded private memory',compiled_execution='Actual owned C++ with pinned CCL provider and observed real host deallocation',source_hashes={p:sha(p) for p in sources},artifacts=artifacts,limitations=limitations,global_readiness_admitted=False)
 (EV/'local-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
 artifacts.append(artifact(EV/'local-proof.json','proof'))
 notes=[]
 for p in sorted(PACKETS.iterdir()):
  req=json.loads((p/'request.json').read_text());t=req['targets'][0];suf=p.name[-2:];range_=next(r for r in native['ranges'] if r['mangled']==t['mangled'])
  originals=[dict(elf_sha256=t['original_elf_sha256'],firmware='RM/RML mixer 13731',role='server',mangled=t['mangled'],address=t['address'],size=t['size'],section='.text')]
  packet=p/'context.json';assert packet.exists()
  own_artifacts=artifacts+[artifact(packet,'packet'),artifact(p/'request.json','packet')]
  checks=[dict(kind=k,argv=['uc-library/.venv/bin/python',str(BASE/'checks.py'),k],timeout_seconds=300) for k in ['format','compile','symbols','native','replay','sanitizers']]
  handoff=dict(version=1,task_id=req['task_id'],namespace=req['namespace'],packet_manifest=str(packet),originals=originals,artifacts=own_artifacts,checks=checks,validation_domain=('1098 native export observations, 61 mix labels x 6 other labels x 3 entry-stack patterns; exact/case/empty/malformed/prefix/linked/parser/sign64/1..32/trailing text; deterministic first12, storage identity. ' if suf=='01' else 'Each exact original variant range separately: null/non-null owned selected x empty/nonempty borrowed-pointer vector. Host checks actual selected, array, CCL child and parameter destruction order and D0 object delete; D1/D2 no object delete. '),limitations=limitations,build_integration=dict(production_partition='RM existing PermissionsComponent.cpp; no new production CPP',public_headers=[sources[0]],test_target='permissions_export_lifecycle_replay',test_sources=[sources[2]],link_dependencies=['presonus_rm_components','pinned CCL corelib and allocator'],ctest_argv=['uc-library/.venv/bin/python',str(BASE/'checks.py'),'replay','--executable','<canonical-built-permissions_export_lifecycle_replay>','--fixture',str(EV/'native-fixtures.json')],fixture=str(EV/'native-fixtures.json')))
  out=BASE/suf;out.mkdir(exist_ok=True);(out/'HANDOFF.json').write_text(json.dumps(handoff,indent=2)+'\n')
  notes.append(dict(elf_sha256=t['original_elf_sha256'],mangled=t['mangled'],work_item_id=req['work_binding']['work_item_id'],date='2026-11-05',status='local_validation_complete_global_admission_pending',observations=limitations,failed_approaches=['Initial linked second-label substring length 1 failed native Aux 9/12; corrected to exact native Aux-prefix length 4; final full replay passed.'] if suf=='01' else [],resolution_condition='Root acceptance, global integration and guarded registry admission; original declaration/ABI/EH questions require independent new evidence.',evidence=[str(EV/'local-proof.json'),str(out/'HANDOFF.json')]))
 (EV/'REMARKS.json').write_text(json.dumps(dict(notes=notes),indent=2)+'\n')
 print('Sealed four exact packet handoffs; no readiness admission.')
if __name__=='__main__':main()
