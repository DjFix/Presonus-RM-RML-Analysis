#!/usr/bin/env python3
"""Package already completed fresh local checks; never edit readiness/global state."""
import datetime,hashlib,json,shlex,shutil,subprocess
from pathlib import Path
BASE=Path('uc-library/candidates/rolling200_02_permissions_lists')
E=Path('evidence/recovery/2026-11-05/permissions-lists01')
W=Path('temp/recovery-work/permissions-lists-local01')
P=Path('temp/recovery-work/rolling200-02/implementation-plan01/packets-current-permissions-lists03-01/packets')
S=['uc-library/include/presonus/mixer/PermissionsComponent.hpp','uc-library/src/Presonus/Mixer/PermissionsComponent.cpp','uc-library/tests/recovery/PermissionsListsReplay.cpp']
PIN='e8cbdea4a4a20e15111f5a690798a259c0374b31'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def art(kind,p):return dict(kind=kind,path=str(p),sha256=sha(p))
def main():
 now=datetime.datetime.now(datetime.timezone.utc).isoformat();checks=[];results=[]
 for k in ['format','compile','symbols','native','replay','sanitizers']:
  log=W/(k+'-final.log');text=log.read_text();assert 'Traceback' not in text
  if k in ['replay','sanitizers']:assert 'Passed 1482 native/provider cases' in text
  if k=='native':assert json.loads((E/'native-proof.json').read_text())['cases']==1482
  shutil.copy2(log,E/log.name)
  check=dict(kind=k,argv=['uc-library/.venv/bin/python',str(BASE/'checks.py'),k],timeout_seconds=120);checks.append(check);results.append(dict(**check,returncode=0,log=art('log',E/log.name)))
 shutil.copy2(W/'commands.jsonl',E/'commands.jsonl')
 for name in ['compile.log','replay.log','replay02.log','replay03.log']:
  if (W/name).exists():shutil.copy2(W/name,E/('development-'+name))
 # Bind actual compile dependencies and official repository sources separately.
 argv=['/usr/bin/c++','-std=c++17','-Ulinux','-Wno-multichar','-Iuc-library/include','-Itemp/core-upstream/root-integration-01/upstream-core/sdk/include/presonus-core-5','-MM',S[1],S[2],'uc-library/src/Presonus/LinkableComponent.cpp']
 deps_raw=subprocess.check_output(argv,text=True);(E/'dependencies.d').write_text(deps_raw)
 deps=sorted({s for s in shlex.split(deps_raw.replace('\\\n',' ')) if not s.endswith(':') and Path(s).is_file()})
 upstream=Path('third_party/ccl-framework')
 assert subprocess.check_output(['git','-C',str(upstream),'rev-parse','HEAD'],text=True).strip()==PIN
 assert subprocess.check_output(['git','-C',str(upstream),'rev-list','--parents','-n','1',PIN],text=True).strip()==PIN
 provider_paths=['core/portable/coreparams.cpp','core/portable/coreparams.h','core/portable/coreparaminfo.h','core/portable/corecomponent.cpp','core/portable/corecomponent.h','core/portable/corestorage.h','core/portable/coreattributes.cpp','core/portable/corepersistence.cpp','core/portable/corefile.cpp','core/public/corestringbuffer.h']
 providers=[]
 for rel in provider_paths:
  path=upstream/rel;blob=subprocess.check_output(['git','-C',str(upstream),'show',PIN+':'+rel]);assert hashlib.sha256(blob).hexdigest()==sha(path);providers.append(art('provider_source',path))
 (E/'provider-dependencies.json').write_text(json.dumps(dict(commit=PIN,root_commit_verified=True,sources=providers,compiled_dependencies=[art('dependency',p) for p in deps],argv=argv),indent=2)+'\n')
 native=json.loads((E/'native-proof.json').read_text())
 limits=[
 'All three void return declarations are provisional source-port choices. Original return types, construction, inheritance, ownership, layout, ARM calling convention and hardware interoperability remain unestablished; declaration-pending only, no local readiness admission.',
 'Original app target/classifier/link/sync ARM instructions execute in Unicorn private memory. All Core/libc/AEABI/file/parameter/storage calls are explicit semantic boundaries. No original Core implementation executes. PC guards include only hash-bound exact app ranges and named boundary addresses; native stores restricted to stack and loading/dirty bytes; input region guard checked per case.',
 'Pinned CCL 5.0.0 implementations provide actual compiled ListParam, NumericParam, StringParam, Component, Attributes, storage and file archives. Provider boundary models are independent of reconstructed C++; observer event agreement includes pinned-provider source behavior and is not proof of historical Core binary equivalence.',
 'mixList/otherList must alias mix/other for list/load calls; optional null mixList is covered only in updateMixPermissionsStrings. Other list and load tag2 parameter are required nonnull. Binding tree, vector, callback projection and link objects are borrowed for each synchronous call. No concurrent mutation, reentrant observer mutation, invalid collection state, >INT_MAX vector sizes or archive exceptions are covered.',
 'Aux projection reads the existing mixer.mixChannels vector and returns actual canonical LinkableComponent objects plus explicit uint32 numeric identity. It assumes neither ChannelComponent inheritance nor native field layout. Replay uses nondereferenced opaque channel identity tokens and actual LinkableComponent::isLinked; no callback link boolean. Nonnull channels require a nonnull projected link.',
 'File boundary in native execution supplies selected fixture filename and source-provider archive result/data; compiled replay uses real canonical getSelectedFileName/getFileName/MixerComponentBase::getDataDir and real CCL archive fixtures. Empty, missing, malformed, successful, missing-key and unmatched persisted values are covered; compressed archives and permission failures are excluded.',
 'Native CCL boundary-model development corrected parameter restoration event ordering to actual parameter-list order and NumericParam float text to upstream %.02f; failures and prior fixture revision are preserved. Final independent native fixtures were regenerated before final compiled replay. No recovered C++ generates expected values.',
 'Existing syncMixStrings was corrected from !=0 to >=0 after exact __aeabi_fcmpge symbol/instruction confirmation. This is an existing-result correction and earns no new current200 target credit. Native/provider -1, -0, +0, +1 and NaN cases cover the corrected predicate; prior source/proofs remain historical and Root must reseal all affected old records.',
 'Local link uses physical pinned provider archives, existing RM archive for canonical getDataDir and section garbage collection. Full Linux/role/install/compile-once/mirror/integration and guarded SQLite admission remain Root-owned. No global CMake, registry, tracker or instruction changes were made by this worker.',
 'REA MCP tools are unavailable; evidence uses existing pyelftools/Unicorn, Linux compiler/nm and official provider source. No REA evidence IDs or setup success is claimed. Sanitizer excludes vptr because the library is compiled without RTTI; ASan and other UBSan checks cover owned replay/source only, with uninstrumented pinned provider archives.'
 ]
 domain=dict(cases=native['cases'],counts={str(i):sum(c['input']['op']==i for c in json.loads((E/'native-fixtures.json').read_text())['cases']) for i in [1,2,3,4]},description='Seven app/selection forms including classifier precedence/case, four initial list sizes, dirty retention, null optional mix list, empty/missing/linked/unlinked aux channels with non-positional and uint32 wrap identities; archive success/failure/defaults, exact saved-text matching and other parameter restore; compare all list strings, max/value, saved text, loading/dirty state and ordered observer events. Five additional existing sync predicate edge cases.')
 correction=dict(mangled='_ZN8Presonus5Mixer20PermissionsComponent14syncMixStringsEv',elf_sha256=native['elf_sha256'],firmware='RM/RML mixer 13731',address=0x50b14,size=152,old_predicate='!= 0.f',new_predicate='>= 0.f',native_compare={'pc':0x50b64,'callee':0x157928,'symbol':'__aeabi_fcmpge'},prior_source_baseline='d548724a88fbb82e34f7a43b1c56081c6afda7c9',old_source_sha256=hashlib.sha256(subprocess.check_output(['git','show','d548724a88fbb82e34f7a43b1c56081c6afda7c9:'+S[1]])).hexdigest(),action='Root must preserve historical source proof and refresh affected existing readiness records under current hashes; not a new target.')
 (E/'sync-correction.json').write_text(json.dumps(correction,indent=2)+'\n')
 remarks=[]
 for packet in sorted(P.iterdir()):
  req=json.loads((packet/'request.json').read_text());target=req['targets'][0]
  remarks.append(dict(date=now,owner='/root/rolling200_02_permissions_lists03',original_elf_sha256=target['original_elf_sha256'],mangled=target['mangled'],unique_work_item=req['work_binding']['work_item_id'],status='compiled_behavior_validated_declaration_pending_not_admitted',remarks=limits,evidence=[str(E/'native-proof.json'),str(E/'local-proof.json')],resolution_or_retry_condition='Root canonical integration and guarded pending admission required. Return declarations require independent evidence before promotion. Consult sync-correction.json before refreshing previous records.'))
 (E/'remarks.json').write_text(json.dumps(remarks,indent=2)+'\n')
 proof=dict(version=1,repository=str(Path.cwd()),baseline='d548724a88fbb82e34f7a43b1c56081c6afda7c9',session='/root/rolling200_02_permissions_lists03',sealed_utc=now,checks=results,source_hashes={p:sha(p) for p in S},native_proof=art('proof',E/'native-proof.json'),domain=domain,limitations=limits,provider=art('proof',E/'provider-dependencies.json'),format_before_source_hashes=True,formatter_version=(E/'format-final.log').read_text().splitlines(),readiness_admitted=False,original_declaration_verified=False,original_arm_abi_verified=False,hardware_validated=False,sync_correction=art('proof',E/'sync-correction.json'))
 (E/'local-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
 artifacts=[art('source',p) for p in S[:2]]+[art('test',S[2])]+[art('replay' if n=='checks.py' else 'producer',BASE/n) for n in ['native_oracle.py','checks.py','seal.py']]
 artifacts += [art('fixture' if p.name=='native-fixtures.json' else 'proof',p) for p in E.iterdir() if p.is_file()]
 artifacts += [art('dependency',p) for p in deps if p not in S]+providers
 archives=['temp/core-upstream/root-integration-01/libpresonus_rm_components.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a','temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a']
 artifacts += [art('dependency',p) for p in archives]+[art('dependency','rootfs/RML16AI_Rack_13731/home/root/mixer')]
 for packet in sorted(P.iterdir()):
  for n in ['context.json','request.json','TASK.md','CONTEXT.md','SOURCE_SLICES.md','ELF_CONTEXT.md','native-context.json']:artifacts.append(art('packet',packet/n))
  req=json.loads((packet/'request.json').read_text());artifacts.append(art('contract',req['reconstruction_contract']['path']))
 for folder in ['permissions-helper-expansions02','permissions-linkable-expansion03']:
  for p in (Path('temp/recovery-work/rolling200-02/implementation-plan01')/folder).rglob('*'):
   if p.is_file():artifacts.append(art('context_expansion',p))
 artifacts.append(art('prior_native_producer','uc-library/candidates/rolling200_02_permissions_readonly/native_oracle.py'))
 unique={a['path']:a for a in artifacts};artifacts=list(unique.values())
 for packet in sorted(P.iterdir()):
  req=json.loads((packet/'request.json').read_text());o=req['originals'][0]['original'];r=next(r for r in native['ranges'] if r['mangled']==o['mangled']);out=BASE/req['task_id'];out.mkdir(exist_ok=True)
  h=dict(version=1,task_id=req['task_id'],namespace=req['namespace'],packet_manifest=str(packet/'context.json'),originals=[dict(elf_sha256=o['elf'],firmware=o['firmware'],role=o['role'],mangled=o['mangled'],demangled=o['demangled'],address=o['address'],size=o['size'],section=r['section'],file_offset=r['file_offset'],range_sha256=r['sha256'])],artifacts=artifacts,checks=checks,validation_domain=domain,limitations=limits,build_integration=dict(production_partition='Existing src/Presonus/Mixer/PermissionsComponent.cpp remains exactly once in PRESONUS_rm_SOURCES. No new production translation unit.',public_headers=[S[0]],test_target='permissions_lists_replay',test_source=S[2],link_dependencies=['canonical presonus_rm_components','pinned CCL corelib and allocator','canonical LinkableComponent source/library','zlib','private glibc29 provider'],ctest_argv=['uc-library/.venv/bin/python',str(BASE/'checks.py'),'replay','--executable','<canonical permissions_lists_replay executable>','--fixture',str(E/'native-fixtures.json')],fixture_binding=art('fixture',E/'native-fixtures.json'),source_placement_review='Existing principal-class files extended; no worker/batch/trial production paths. Root owns all shared CMake/public lists/integration.',root_required='Review sync correction and refresh affected historical records. Root retains full Linux/role/install/compile-once/mirror/active-source checks, pending fragments, merge_readiness.py --dry-run and guarded SQLite admission. Worker supplies HANDOFF, not readiness fragments.'))
  (out/'HANDOFF.json').write_text(json.dumps(h,indent=2)+'\n')
 print(json.dumps(dict(handoffs=3,cases=native['cases'],checks=6,admitted=False)))
if __name__=='__main__':main()
