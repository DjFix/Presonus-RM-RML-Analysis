#!/usr/bin/env python3
"""Seal completed local evidence; no global build or readiness mutation."""
import datetime,hashlib,json,shlex,shutil,subprocess
from pathlib import Path
from check import BASE,WORK,EVIDENCE,SOURCES,SDK,PACKETS
PIN='e8cbdea4a4a20e15111f5a690798a259c0374b31'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def art(kind,p):return dict(kind=kind,path=str(p),sha256=sha(p))
def main():
 EVIDENCE.mkdir(parents=True,exist_ok=True);now=datetime.datetime.now(datetime.timezone.utc).isoformat();checks=[];results=[]
 for kind in ['format','compile','symbols','native','replay','sanitizers','regressions']:
  p=WORK/(kind+'-final.log');text=p.read_text();assert 'Traceback' not in text
  if kind in ['replay','sanitizers']:assert 'Passed 159 independent native/provider cases' in text
  if kind=='regressions':
   for count in [1190,1482,1110]:assert str(count) in text
  shutil.copy2(p,EVIDENCE/p.name)
  check=dict(kind=kind,argv=['uc-library/.venv/bin/python',str(BASE/'check.py'),kind],timeout_seconds=120)
  checks.append(check);results.append(dict(**check,returncode=0,log=art('log',EVIDENCE/p.name)))
 shutil.copy2(WORK/'commands.jsonl',EVIDENCE/'commands.jsonl')
 for p in WORK.glob('*0*.log'):shutil.copy2(p,EVIDENCE/('development-'+p.name))
 shutil.copy2(WORK/'regress.py',EVIDENCE/'development-copy-regress.py')
 argv=['/usr/bin/c++','-std=c++17','-Ulinux','-Wno-multichar','-Iuc-library/include','-I'+str(SDK/'include/presonus-core-5'),'-MM']+[p for p in SOURCES if p.endswith('.cpp')]
 raw=subprocess.check_output(argv,text=True);(EVIDENCE/'dependencies.d').write_text(raw)
 deps=sorted({p for p in shlex.split(raw.replace('\\\n',' ')) if not p.endswith(':') and Path(p).is_file()})
 upstream=Path('third_party/ccl-framework')
 assert subprocess.check_output(['git','-C',str(upstream),'rev-parse','HEAD'],text=True).strip()==PIN
 assert subprocess.check_output(['git','-C',str(upstream),'rev-list','--parents','-n','1',PIN],text=True).strip()==PIN
 provider_files=['core/portable/coreparams.cpp','core/portable/coreparams.h','core/portable/coreparaminfo.h','core/portable/corecomponent.cpp','core/portable/corecomponent.h','core/portable/corestorage.h','core/portable/coreattributes.cpp','core/portable/corepersistence.cpp','core/portable/corefile.cpp','core/public/corestringbuffer.h','core/public/corevector.h','core/system/coredebug.cpp','core/system/coredebug.h']
 providers=[]
 for rel in provider_files:
  path=upstream/rel;blob=subprocess.check_output(['git','-C',str(upstream),'show',PIN+':'+rel]);assert hashlib.sha256(blob).hexdigest()==sha(path);providers.append(art('provider_source',path))
 (EVIDENCE/'provider-dependencies.json').write_text(json.dumps(dict(commit=PIN,root_commit_verified=True,sources=providers,dependencies=[art('dependency',p) for p in deps],argv=argv),indent=2)+'\n')
 native=json.loads((EVIDENCE/'native-proof.json').read_text());rows=json.loads((BASE/'fixtures.json').read_text())['cases']
 limits=[
 'Portable application source port only. Constructor parameter identity is encoded; other original returns, original class layout/inheritance/ownership, ARM calling convention and hardware interoperability remain unresolved. getClient uses a provisional const ClientSubscription* return. No readiness admission.',
 'Both original RM and CS18 C1 identities have separate ELF SHA/range/section mappings, private-memory native executions and exact host symbol checks. Same source body does not transfer readiness. Compiler also emits C2 but no additional original C2 identity is admitted or claimed.',
 'Native constructor stores identifier, zeroes words +8/+12/+20 and byte +16, constructs six empty CString64 heads; +4 and all 63-byte tails are explicitly verified unchanged under sentinel-prefilled native memory. Portable fields are named only by observed offsets; no initialized native +4 field was invented. Real CCL placement construction independently preserves six string tails.',
 'setSelectedClient/copyToSelected require nonnull nonalias terminated source buffers. Actual prior source-port snapshot deallocation precedes actual allocation; both native traces and host allocator instrumentation observe order. Null/alias inputs, allocation failures, exceptions, concurrent/reentrant mutation and oversized collections are excluded. Alias is defensively rejected in the source port. Legacy external snapshots remain borrowed.',
 'copyToSelected copies five strings in observed native +18,+98,+d8,+58,+118 order; initializes new scalar state through actual constructor and leaves sixth string empty. Unspecified tails are not copied by these setters. Existing SourcePortValues preserves full three-buffer values for prior getter regression domains. portableOwnSelected copies the entire extended source-port state so saved identity/lifetime remain consistent.',
 'Client collection is an actual CCL Vector with explicit source-port bindClients; binding updates legacy public clientCount and numClients/getClient enforce the bound invariant. Old unbound independent numClients count remains usable; getClient requires a bound nonempty collection. Null slots and signed negative/out-of-range indices are covered. This is an intentional source binding, not original field/layout recovery.',
 'updateDevices uses actual pinned ListParam, recognized app filtering, last eligible selection when saved identity is empty, last equal identity otherwise, default index zero if unmatched, no-devices label, setValue(false), changed then rangeChanged. Constructor/filter/display/archive/type/parameter and AEABI native boundaries are named models, not executions of original Core; no original Core body is decompiled or executed. Existing independent native getter/list regression fixtures validate classifier/display/provider choices separately.',
 'init substitutes actual ParamInfo::kString discriminator for historical RTTI because pinned CCL is built without RTTI. With a consistent genuine StringParam object it sets default12345 then runs canonical loadAccessCode and updateDevices. Real CCL file archives cover absent, empty and persisted access code. Numeric/null tags are covered with missing matching stored keys; forged inconsistent parameter types and archive exceptions are excluded.',
 'Native application ranges run under Unicorn with explicit PC allowlist; stores are restricted to private mapped object/stack memory and all call/write traces retained. Core/libc/AEABI boundaries are explicit semantic models; this proves the stated bounded application domain and actual compiled provider agreement, not historical Core equivalence or original ARM ABI.',
 'Provider is official pinned CCL 5.0.0 root commit, checked from fetched local Git history and file blobs. Physical local SDK/static archives supply actual CCL implementations; no fake Core providers. Sanitizer excludes vptr due no RTTI and provider archives are uninstrumented. No REA MCP tools are available; existing pyelftools/Unicorn/compiler/nm evidence is used without claiming REA IDs.',
 'Development failures are preserved: initial oracle fixed-width string read crossed stack mapping; replay parser needed to preserve real DebugPrintf lines; deep absolute archive fixture path exceeded bounded FileName capacity, corrected to short project-relative directories and explicit directory creation. Expected fixture values were not changed to match recovered C++; final independent native output was reproduced byte-for-byte.',
 'Root owns global CMake, source partitions/public lists, full Linux/role/install/compile-once/active-source/mirror checks, merge_readiness dry-run, SQLite admission and tracker/history persistence. Local check success is not global acceptance. Diagnostic updateDevices DebugPrintf messages are excluded from the portable observable domain; final parameter notifications are preserved.'
 ]
 domain=dict(cases=len(rows),counts={op:sum(r['input']['op']==op for r in rows) for op in ['ctor','get','copy','set','update','init']},description='Per-ELF sentinel constructors and scalar extremes; signed collection boundaries/null slots; replacement from absent/owned snapshot, empty/63-byte strings and observed allocator order; six client populations, saved identity null/empty/matching/duplicate/unmatched, old list lengths 0/3, exact final strings/value/filtered identifiers and ordered observer messages; actual StringParam default/load archive outcomes and nonstring/null tags.',additional_source_port_invariant=True,regressions=dict(readonly=1190,lists=1482,export_lifecycle=1110))
 remarks=[]
 for packet in sorted(PACKETS.iterdir()):
  req=json.loads((packet/'request.json').read_text())
  for o in req['originals']:
   o=o['original'];remarks.append(dict(date=now,owner='/root/rolling200_02_permissions_selection19',original_elf_sha256=o['elf'],mangled=o['mangled'],unique_work_item=req['work_binding']['work_item_id'],status='compiled_behavior_validated_declaration_pending_not_admitted',remarks=limits,evidence=[str(EVIDENCE/'native-proof.json'),str(EVIDENCE/'local-proof.json')],resolution_or_retry_condition='Root canonical integration/guarded admission and historical active-source reseals; independent original return/layout evidence required for broader promotion. Consult these notes before subsequent work; no reconstruction retry without changed inputs.'))
 (EVIDENCE/'remarks.json').write_text(json.dumps(remarks,indent=2)+'\n')
 proof=dict(version=1,repository=str(Path.cwd()),baseline='13c6cf5303f330db4c359986439577d611b65c85',session='/root/rolling200_02_permissions_selection19',sealed_utc=now,checks=results,source_hashes={p:sha(p) for p in SOURCES},native_proof=art('proof',EVIDENCE/'native-proof.json'),provider=art('proof',EVIDENCE/'provider-dependencies.json'),validation_domain=domain,limitations=limits,format_before_source_hashes=True,formatter_version=(EVIDENCE/'format-final.log').read_text(),readiness_admitted=False,original_declaration_verified=False,original_arm_abi_verified=False,hardware_validated=False)
 (EVIDENCE/'local-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
 artifacts=[art('source' if i<6 else 'test',p) for i,p in enumerate(SOURCES)]+[art('replay' if p.name=='check.py' else 'fixture' if p.name=='fixtures.json' else 'producer',p) for p in BASE.iterdir() if p.is_file()]
 artifacts += [art('proof',p) for p in EVIDENCE.iterdir() if p.is_file()]+providers+[art('dependency',p) for p in deps if p not in SOURCES]
 for p in ['temp/core-upstream/root-integration-01/libpresonus_rm_components.a',str(SDK/'lib/libcorelib.a'),str(SDK/'lib/libpresonus_core_allocator.a'),'temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a','rootfs/RML16AI_Rack_13731/home/root/mixer','rootfs/CS18_v13840/home/root/surface']:artifacts.append(art('dependency',p))
 for packet in sorted(PACKETS.iterdir()):
  req=json.loads((packet/'request.json').read_text())
  for n in ['context.json','request.json','TASK.md','ELF_CONTEXT.md','SOURCE_SLICES.md','CONTEXT.md','native-context.json']:artifacts.append(art('packet',packet/n))
  artifacts.append(art('contract',req['reconstruction_contract']['path']))
 for row in json.loads((EVIDENCE/'copied-inputs.json').read_text()):artifacts.append(art('historical_input',row['relative']))
 artifacts=list({a['path']:a for a in artifacts}.values())
 for packet in sorted(PACKETS.iterdir()):
  req=json.loads((packet/'request.json').read_text());originals=[]
  for item in req['originals']:
   o=item['original'];r=next(r for r in native['ranges'] if r['mangled']==o['mangled'] and r['elf_sha256']==o['elf']);originals.append(dict(elf_sha256=o['elf'],firmware=o['firmware'],role=o['role'],mangled=o['mangled'],demangled=o['demangled'],address=o['address'],size=o['size'],section=r['section'],file_offset=r['file_offset'],range_sha256=r['sha256']))
  out=Path('uc-library/candidates')/req['task_id'];out.mkdir(parents=True,exist_ok=True)
  h=dict(version=1,task_id=req['task_id'],namespace=req['namespace'],packet_manifest=str(packet/'context.json'),originals=originals,artifacts=artifacts,checks=checks,validation_domain=domain,limitations=limits,build_integration=dict(production_partition='Add src/Presonus/UC/ClientSubscription.cpp exactly once to PRESONUS_common_SOURCES: both RM and CS18 C1 identities. Existing MixerComponentBase.cpp and PermissionsComponent.cpp retain exactly-once PRESONUS_rm_SOURCES placement.',public_headers=SOURCES[0:6:2],test_target='permissions_selection_replay',test_source=SOURCES[-1],link_dependencies=['canonical presonus_rm_components and common ClientSubscription source','pinned CCL corelib and allocator','private glibc29 provider','zlib'],ctest_argv=['uc-library/.venv/bin/python',str(BASE/'check.py'),'replay','--executable','<canonical permissions_selection_replay executable>','--fixture',str(BASE/'fixtures.json')],fixture_binding=art('fixture',BASE/'fixtures.json'),source_placement_review='Canonical existing principal-class files extended; one new principal-class implementation, no duplicate class or task-named production path.',root_required='Global integration, full Linux/role/install/compile-once/mirror, active-source reseals for all affected historical proofs and guarded pending admission. Persist linked remarks in operational history. Worker supplies six HANDOFFs for seven original identities, no readiness fragments or global mutations.'))
  (out/'HANDOFF.json').write_text(json.dumps(h,indent=2)+'\n')
 print(json.dumps(dict(handoffs=6,elf_identities=7,cases=len(rows),readiness_admitted=False)))
if __name__=='__main__':main()
