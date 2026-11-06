"""Seal current worker evidence; never mutates registry/shared integration."""
import datetime,hashlib,json,re,subprocess,os
from pathlib import Path
BASE=Path('uc-library/tests/recovery/card_handler_lifecycle_properties');OUT=Path('evidence/recovery/2026-11-06/rolling200-02/handler132-nortti265');WORK=Path('temp/recovery-work/rolling200-02/handler132-nortti265');PACKETS=Path('temp/recovery-work/rolling200-02/next-implementation132/prepared132/packets')
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bound(kind,p):return dict(kind=kind,path=str(p),sha256=digest(p))
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2)+'\n')
sources=['uc-library/src/Presonus/NOAA/TCardHandlerLifecycle.cpp','uc-library/src/Presonus/NOAA/TCardHandlerProperties.cpp','uc-library/src/Presonus/NOAA/TCardHandlerEventQueue.cpp','uc-library/src/Presonus/NOAA/TCardHandlerEvents.cpp','uc-library/src/Presonus/NOAA/TCardHandlerRelease.cpp']
headers=['uc-library/include/presonus/noaa/card_handler.hpp','uc-library/include/presonus/noaa/card_handler_state.hpp','uc-library/include/presonus/noaa/card_handler_events.hpp']
test='uc-library/tests/recovery/CardHandlerLifecyclePropertiesReplay.cpp'
fixture=json.loads((BASE/'fixtures.json').read_text());replay=json.loads((OUT/'replay.json').read_text());symbols=json.loads((OUT/'symbols.json').read_text());producer=digest(BASE/'check.py')
commands=[]
for p in sorted((OUT/'runs').glob('*/*.command.json')):
 c=json.loads(p.read_text())
 if c['producer_sha256']==producer and c.get('input_sha256') and all(digest(path)==h for path,h in c['input_sha256'].items()):commands.append(dict(path=str(p),sha256=digest(p),**c))
assert commands and all(c['returncode']==0 for c in commands),'Final producer has a failed check: fix before seal'
for name in ['native','format','compile0','compile1','compile2','compile3','compile4','compile5','link','symbol0','symbol1','lifecycleC1D01','lifecycleC2D21','failure-C2-register-True','release-replay','canonical-ctest']:
 assert any(Path(c['path']).name==name+'.command.json' for c in commands),name
assert symbols['names_match'] and replay['fixture_sha256']==digest(BASE/'fixtures.json')
deps=set()
for p in WORK.glob('unit*.d'):
 text=p.read_text().replace('\\\n',' ')
 for word in text.split()[1:]:
  dep=Path(word)
  if dep.is_file() and not dep.is_absolute():deps.add(dep)
provider_sources=['uc-library/src/Presonus/NOAA/TCardFirmware.cpp','uc-library/src/Presonus/NOAA/TCardLifecycle.cpp','uc-library/src/Presonus/NOAA/TCardSerial.cpp','uc-library/src/Presonus/NOAA/TCardRouterLifecycle.cpp','uc-library/src/Presonus/NOAA/TCardSPIService.cpp','third_party/ccl-framework/core/system/corethread.cpp','third_party/ccl-framework/core/platform/shared/posix/corethread.posix.cpp','third_party/ccl-framework/core/system/coreatomicstack.cpp','third_party/ccl-framework/core/portable/corealloc.cpp']
for p in provider_sources:
 if Path(p).is_file():deps.add(Path(p))
upstream_blobs=[]
for path in sorted(deps):
 if path.parts[:2] != ('third_party','ccl-framework'):continue
 relative=str(Path(*path.parts[2:]));prefix=['git','-C','third_party/ccl-framework']
 expected=subprocess.check_output([*prefix,'rev-parse','HEAD:'+relative],text=True).strip()
 actual=subprocess.check_output([*prefix,'hash-object','--',relative],text=True).strip()
 assert actual==expected,('Changed upstream provider',str(path))
 upstream_blobs.append(dict(path=str(path),blob_sha1=actual,sha256=digest(path)))
archives=['temp/core-upstream/root-integration-01/libpresonus_uc.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a','temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a']
prior=sorted(Path('evidence/recovery/2026-11-06/rolling200-02/handler-next123/prior-research132').rglob('EVIDENCE.json'))
assert len(prior)==6
notes=[]
for i,r in enumerate(fixture['ranges'],1):
 notes.append(dict(elf_sha256=r['elf_sha256'],mangled=r['mangled'],unique_work_item=json.loads((PACKETS/f'rolling200_02_handler132_{i:02}'/'request.json').read_text())['work_binding']['work_item_id'],date='2026-11-06',status='implemented-local-validation-passed-not-admitted',resolved='Actual delivered Card lifecycle/firmware/serial and Router providers reused. Earlier pure-virtual Card blocker resolved.',observations=['Native setProperty serial/erase/purge IDs take main lock before purge (0x9f1a8/0x9f0a8/0x9f34c); update/script purge before main lock (0x9f258/0x9f2f8). Preserve instruction order despite earlier prose shorthand.','C1/C2 failure continuations delete only failed unconstructed dependency storage. Earlier completed registered Card/Router dependencies are retained, not silently reclaimed by RAII. Twenty portable failure cases compare registration retention and application-cleanup projections against original landing instructions.','Source-port pool capacities are explicitly64/64/64. Source-port invalid sizes/missing projections reject. Exhausted-pool stop returns rather than reproducing native null memcpy. Typed payload snapshots own complete explicitly supplied application bytes.','Original ordinary return declarations, object layout, ARM ABI, legacy exception dispatcher and hardware equivalence remain unresolved. Root integration265 noRTTI test failure corrected with exact typed-constructor base identities and strict unknown-receiver rejection; all original order/cleanup assertions retained.'],retry_condition='Resolve declarations/layout only from independent evidence. Original full EHABI unwinder or hardware claims require separate authorized proof; no unchanged-blocker retries.',evidence=['uc-library/tests/recovery/card_handler_lifecycle_properties/fixtures.json','evidence/recovery/2026-11-06/rolling200-02/handler132-nortti265/PROOF.json'],prior_reviews=[dict(path=str(p),sha256=digest(p)) for p in prior]))
write(OUT/'NOTES.json',notes)
limitations=[
 'Portable C++ source port with exact encoded symbol identities; original unencoded ordinary return declarations, full object/member layout, calling convention/ARM ABI and hardware behavior are unverified.',
 'Upstream Core comes solely from official CCL5.0.0 e8cbdea4a4a20e15111f5a690798a259c0374b31. Actual modern Thread/Lock/LinkedList/AtomicStackLocked/Singleton implementations are used; no Core firmware body executes or is reconstructed.',
 'Native oracle executes six exact ELF ranges, private application memory, and explicit rejecting provider boundaries. Constructor failure cases inject exception identity and enter reviewed application landing continuations; the original EHABI language-unwinder selection/dispatch does not execute. C++ exceptions use the actual host runtime.',
 'Native completed dependency retention and failed-storage delete are preserved. Portable owned pool storage is reclaimed on failure/destruction. Additional modern queue/pool allocations and provider-owned runtime storage have no original native field/cardinality claim.',
 'Native destructor always terminates; modern POSIX unstarted-thread termination is invalid, so owned start flag guards it and started destruction joins. Borrowed callers retain their documented start/join/lifetime obligation. Raw original failure-retained dependencies remain registered as observed; the failure replay observes them before explicit test-owned cleanup.',
 'Finite pools64/64/64 belong to each portable queue; original static global-pool contention across Handler instances is unverified. The capacities are an explicit source-port selection. Invalid semantic sizes (<8/>512), undersized immediate payloads and absent/mismatched live projections fail closed. Native stop-while-starved null memcpy is replaced with a safe return. Untyped arbitrary host Property payload images are never copied.',
 'Native byte-valued bool arguments are compared by bool truth (host C++ canonicalizes bool); native full word/int and low-byte argument projections remain separately checked. Original byte/pointer/layout ABI is unclaimed.',
 'Successful provider calls forward real Card/Router/CCL bodies. Constructor-failure tests explicitly inject exceptions before selected provider bodies and preserve the observed app-level cleanup/retention; these injected cases are a separate boundary domain. SPI/GPIO/serial/file/network/ioctl host boundaries are rejecting/offline before construction; observer/listener/HAL test doubles capture external boundaries and do not synthesize Card update success or device responses. Real Card numeric firmware returns2008 and0 are observed. No actual device programming, erase, flashing, serial/network I/O or host-syscall forwarding from guest code occurs.',
 'Full canonical Linux CTest, installed-role/compile-once audits, active-source admission, trackers and registry publication remain Root-owned. This delivery contains no readiness fragments or registry mutations.'
]
proof=dict(version=1,task='rolling200_02_handler132',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),checkout=str(Path.cwd()),baseline='161d338c59109192c51fdb92cd7f42a8ecf20b44',worker_agent='/root/rolling200_02_handler132',process_thread_id=os.environ.get('CODEX_THREAD_ID'),session_id_note='Exact model-session and cumulative-token accounting remain coordinator-owned; no estimates supplied.',originals=fixture['ranges'],native_executions=len(fixture['cases']),native_producer=bound('producer',BASE/'native.py'),fixture=bound('fixture',BASE/'fixtures.json'),formatted_sources=[bound('source',p) for p in sources+headers+[test]],dependencies=[bound('dependency',p) for p in sorted(deps)],linked_archives=[bound('archive',p) for p in archives],core_commit=subprocess.check_output(['git','-C','third_party/ccl-framework','rev-parse','HEAD'],text=True).strip(),formatter_version=subprocess.check_output(['uc-library/.venv/bin/clang-format','--version'],text=True).strip(),compiler_version=subprocess.check_output(['c++','--version'],text=True).splitlines()[0],upstream_blobs=upstream_blobs,command_receipts=commands,compiled_symbols=symbols,replay=replay,limitations=limitations,native_core_executed=False,device_operations=0,readiness_admitted=False)
write(OUT/'PROOF.json',proof)
common=[bound('correction-provenance',OUT/'CORRECTION_PROVENANCE.json'),bound('nortti-proof',OUT/'NO_RTTI.json')]+[bound('source',p) for p in sources+headers]+[bound('test',test),bound('fixture',BASE/'fixtures.json'),bound('replay',BASE/'check.py'),bound('producer',BASE/'native.py'),bound('producer',BASE/'seal.py'),bound('proof',OUT/'PROOF.json'),bound('remarks',OUT/'NOTES.json')]
existing={a['path'] for a in common}
for p in sorted(deps):
 if str(p) not in existing:common.append(bound('dependency',p));existing.add(str(p))
for p in archives+['AGENTS.md','docs/worker-handoff.md','docs/core-framework-lineage.md','evidence/recovery/2026-11-06/rolling200-02/handler-next123/PROVIDER_RESOLVED132.json','rootfs/RML16AI_Rack_13731/home/root/mixer','evidence/recovery/2026-11-05/rolling200-02/handler-release/replay.py','evidence/recovery/2026-11-05/rolling200-02/handler-release/fixture.txt']:
 if p not in existing:common.append(bound('dependency',p));existing.add(p)
for p in prior:common.append(bound('historical-review',p))
wraps=sorted(set(re.findall(r'__wrap_([a-zA-Z0-9_]+)\s*\(',Path(test).read_text())))
for i,r in enumerate(fixture['ranges'],1):
 task=f'rolling200_02_handler132_{i:02}';packet=PACKETS/task
 manifest=packet/'context.json';assert manifest.is_file()
 artifacts=common+[bound('packet',packet/n) for n in ['context.json','request.json','native-context.json','TASK.md','ELF_CONTEXT.md','SOURCE_SLICES.md','CONTEXT.md']]
 checks=[dict(kind=mode,argv=['uc-library/.venv/bin/python',str(BASE/'check.py'),mode],timeout_seconds=180) for mode in ['native','format','compile','symbols','replay','regressions','ctest']]
 integration=dict(production_partition='RM (original server identities; Root verifies exactly-one OBJECT partition)',new_cpp=['uc-library/src/Presonus/NOAA/TCardHandlerLifecycle.cpp'],modified_cpp=sources[1:3],public_headers=headers,test_targets=['noaa_tcard_handler_lifecycle_properties_replay'],test_source=test,link_dependencies=['presonus::rm_components','pinned CCL corelib','presonus_core_allocator','existing Linux private provider'],link_wraps=wraps,ctest_argv=['uc-library/.venv/bin/python',str(BASE/'check.py'),'replay','--executable','$<TARGET_FILE:noaa_tcard_handler_lifecycle_properties_replay>','--fixtures',str(BASE/'fixtures.json'),'--fixture-sha256',digest(BASE/'fixtures.json')],fixture_sha256=digest(BASE/'fixtures.json'),additional_regressions='check.py regressions compiles/runs existing Handler+deferred+five thread modes+release/Card lifecycle/Card serial/Router lifecycle consumers; exact argv retained in PROOF command receipts')
 handoff=dict(version=1,task_id=task,namespace='Presonus::NOAA',packet_manifest=str(manifest),originals=[{k:r[k] for k in ['elf_sha256','firmware','role','mangled','address','size','section']}],artifacts=artifacts,checks=checks,validation_domain='All27 literal immediate IDs across99 native/real-provider comparisons; Card modes0/1/2/other; word, byte and bool argument projections; setup/start and serial/erase/update/script branch order and lock scopes. Actual C1/C2/D0/D1/D2 success lifecycle, registration and singleton equality; original D0 operator-delete invocation and actual host D0 frees distinguished from D1/D2 retained root storage. Twenty constructor allocation/provider failure landing-continuation comparisons preserve failed-storage deletion and completed provider retention. All pool boundaries8/16/17/32/33/512, starvation sleep4, mixed FIFO, complete payload lifetime copies, safe stopped exhaustion, deterministic link-allocation cleanup and undersized rejection. Existing consumer replays are separate domains.',limitations=limitations,build_integration=integration)
 write(Path('uc-library/candidates')/task/'HANDOFF.json',handoff)
print('Sealed six identity-specific HANDOFF v1 files and current shared proof')
