"""Seal bounded worker evidence and exact v1 packet handoffs; no admission."""
import datetime, hashlib, json, platform, subprocess
from pathlib import Path
BASE=Path('uc-library/tests/recovery/fpga_programming')
OUT=Path('evidence/recovery/2026-11-05/rolling200-02/fpga-resume18')
WORK=Path('temp/recovery-work/rolling200-02/fpga-resume18')
PACKETS=Path('temp/recovery-work/rolling200-02/next-implementation18/prepared-fpga-resume18/packets')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2)+'\n')
fixtures=json.loads((BASE/'fixtures.json').read_text())
replay=json.loads((OUT/'replay.json').read_text());assert replay['fixture_sha256']==sha(BASE/'fixtures.json') and all(c['passed'] for c in replay['cases'])
deps=set(['uc-library/src/Presonus/NOAA/TCardFPGAUpdater.cpp','uc-library/include/presonus/noaa/TCardFPGAUpdater.hpp','uc-library/tests/recovery/TCardFPGAProgrammingReplay.cpp',str(BASE/'native.py'),str(BASE/'check.py'),str(BASE/'seal.py'),str(BASE/'fixtures.json'),'uc-library/candidates/rolling200_02_stage03_w06/parked_methods.cpp','uc-library/candidates/rolling200_02_stage03_w06/replay.cpp','uc-library/tests/recovery/FPGADeletingDestructorReplay.cpp','evidence/recovery/2026-11-05/rolling200-02/updater02/fixtures.txt','evidence/recovery/2026-11-05/rolling200-02/updater02/native-observations.json','evidence/recovery/2026-11-05/rolling200-02/updater02/proof.json','AGENTS.md','docs/worker-handoff.md','docs/core-framework-lineage.md'])
for p in WORK.glob('*.d'):
    text=p.read_text().replace('\\\n',' ');deps.update(x for x in text.split(':',1)[1].split() if Path(x).is_file() and not x.startswith('/usr/'))
for p in [Path('temp/core-upstream/root-integration-01/libpresonus_uc.a'),Path('temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a'),Path('temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a'),Path('temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a')]:deps.add(str(p))
for p in (OUT/'pack32-expansion').iterdir():deps.add(str(p))
for suffix in ['03','04']:
    packet=PACKETS/('rolling200_02_fpga_resume18_'+suffix)
    for p in packet.iterdir():
        if p.is_file():deps.add(str(p))
    deps.add(f'temp/recovery-work/rolling200-02/next-implementation18/rolling200_02_fpga_resume18_{suffix}.contract.json')
commands={str(p):json.loads(p.read_text()) for p in OUT.rglob('*.command.json')}
assert commands and all(c['returncode']==0 for c in commands.values())
# Every run retains exact argv, timestamps, outputs and durations. Earlier
# replay comparison adapter failure is preserved explicitly in remarks.
for name in ['format','compile0','link','symbols','native','nonprogramming-replay','lifecycle-replay']:
    assert any(p.endswith('/'+name+'.command.json') for p in commands),name
limitations=fixtures['limitations']+[
 'Source-model ordinary bool waitFirmwareCommand and int update returns are candidates: encoded parameter/scope identity and bounded return-word behavior do not prove exact original return declarations.',
 'Shared epoch is the existing updater source-port setter/storage; no cross-class original global linkage, layout, inheritance, ARM calling convention, binary interoperability or thread-safety claim.',
 'Native Core time/division/debug/sleep/string formatting, libc memory, FirmwareBundle stream, SysexReceiver waitResponseSet and virtual transport boundaries are scripted. Actual source-port providers and real CCL/zlib execute in the host replay; this is not native firmware/provider equivalence.',
 'Native stack image tail is zero-seeded for initial partial words, then retained from prior blocks. Other first-tail values are outside the equivalence domain.',
 'Negative read -1 from actual corrupted gzip is an explicit portable safety adaptation (close and2003) instead of original unsafe/unbounded processing; count>200 guard is unobserved safety protection against a contract-violating provider.',
 'Original block-response timeout returns2000 without closeBinImage. Replay records zero cleanup calls, then closes solely in fixture teardown after emitting observations; this is not claimed production cleanup.',
 'Existing nonprogramming native fixtures remain historical hash-bound observations; their1868 host regression cases were freshly replayed. D0/D1/D2 host regressions freshly verify actual unregister/free lifecycle. Those identities are not reconstructed or promoted by this delivery.',
 'Native waitResponseSet is a contract trap verifying pointer/timeout. Actual portable provider is replayed with scripted pump/timeout response; its native implementation is outside these two target bodies.',
 'No device, network, serial, ioctl, flashing, actual FPGA CRC/hardware interaction or guest host-syscall passthrough. Host SPI IO is injected; accidental open/ioctl/socket paths abort.',
 'Initial cold cadence and bounded single-thread transactions only; repeated-object global cadence lifetime/concurrency, exceptions and allocation failure are excluded.'
]
notes=[]
for r in fixtures['ranges'][:2]:
    notes.append(dict(date=datetime.datetime.now(datetime.timezone.utc).isoformat(),original_elf_sha256=r['elf_sha256'],mangled=r['mangled'],status='compiled_pending_original_declaration_root_gates',owner='/root/rolling200_02_fpga_resume18',evidence=[str(OUT/'proof.json'),str(BASE/'fixtures.json'),str(OUT/'replay.json')],remarks=limitations,resolution_or_retry_condition='Root reviews bounded implementation, runs accept_worker and canonical Linux/full CTest/role/install/compile-once/active-source/admission gates. Ready promotion additionally needs independent original return declarations and explicit treatment of declared provider differences; never infer original bool/int from mangling or r0.',prior_observation_resolution='Historical programming execution pause superseded only for private Unicorn memory by the bound Root resume18 contract. parked_methods.cpp retained unchanged; setter resolves its anonymous external epoch link in canonical source.'))
write(OUT/'REMARKS.json',dict(version=1,notes=notes,corrected_fixture_adapter_failure=dict(case='wait_empty_command_message',observation='First expanded replay passed integer2 to an adapter that still selected wait instead of empty string. Native observation and production method were unchanged. Corrected only the host argument adapter; all45 final cases pass.',native_or_production_semantics_changed=False)))
write(OUT/'proof.json',dict(version=1,worker_session='/root/rolling200_02_fpga_resume18',checkout=str(Path.cwd()),base_commit='13c6cf5303f330db4c359986439577d611b65c85',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='Two portable coordinator methods; no readiness admission',host=platform.platform(),ranges=fixtures['ranges'],native_original_cases=len(fixtures['cases']),per_target_native_cases={r['mangled']:sum(c['expected']['instruction_counts'][str(r['address'])]>0 for c in fixtures['cases']) for r in fixtures['ranges'][:2]},portable_cases=len(replay['cases']),historical_nonprogramming_fixture_replays=1868,unicorn_version=fixtures['unicorn_version'],formatter_version=subprocess.check_output(['uc-library/.venv/bin/clang-format','--version'],text=True).strip(),ccl_pinned_commit=subprocess.check_output(['git','-C','third_party/ccl-framework','rev-parse','HEAD'],text=True).strip(),elf_sha256=fixtures['elf_sha256'],fixture_sha256=sha(BASE/'fixtures.json'),sources={p:sha(p) for p in sorted(deps)},commands=commands,isolation=fixtures['isolation'],namespace_and_mangling_verified=True,compilation_and_replay_passed=True,formatting_verified=True,original_declaration_verified=False,original_arm_abi_verified=False,hardware_verified=False,core_binary_bodies_executed=False,limitations=limitations))
deps.update([str(OUT/'proof.json'),str(OUT/'REMARKS.json'),str(OUT/'replay.json'),str(OUT/'symbols.json')])
for p in OUT.rglob('*'):
    if p.is_file():deps.add(str(p))
checks=[dict(kind=k,argv=['uc-library/.venv/bin/python',str(BASE/'check.py'),m],timeout_seconds=180) for k,m in [('format','format'),('compile','compile'),('symbols','symbols'),('native','native'),('replay','replay'),('regression','regressions')]]
for suffix in ['03','04']:
    task='rolling200_02_fpga_resume18_'+suffix;packet=PACKETS/task;request=json.loads((packet/'request.json').read_text());original=request['originals'][0]['original'];r=next(r for r in fixtures['ranges'] if r['mangled']==original['mangled']);manifest=str(packet/'context.json')
    artifacts=[]
    for p in sorted(deps):
        kind='source'
        if p==str(OUT/'proof.json'):kind='proof'
        elif p==str(BASE/'fixtures.json'):kind='fixture'
        elif p==str(BASE/'check.py'):kind='replay'
        elif p=='uc-library/tests/recovery/TCardFPGAProgrammingReplay.cpp':kind='test'
        elif p.startswith('evidence/'):kind='evidence'
        elif p.startswith('temp/'):kind='dependency'
        artifacts.append(dict(kind=kind,path=p,sha256=sha(p)))
    handoff=dict(version=1,task_id=task,namespace='Presonus::NOAA::TCardFPGAUpdater',packet_manifest=manifest,originals=[dict(elf_sha256=r['elf_sha256'],firmware=r['firmware'],role=r['role'],mangled=r['mangled'],demangled=original['demangled'],address=r['address'],size=r['size'],section=r['section'],section_index=r['section_index'],file_offset=r['file_offset'],range_sha256=r['range_sha256'])],artifacts=artifacts,checks=checks,validation_domain='Original wait/update/pack32 ARM instructions in bounded private Unicorn memory;44 native executions,45 portable cases including explicit corrupted-gzip safety adaptation; zero/1/2/3/4/5/199/200/201/399/400/4201/25601-byte image domains,128-sequence wrap, status/sequence/timeouts at erase/block/finish, actual stream cleanup, cancellation, signed timeout equality/min/max, low-word elapsed wrap, backward/negative clock, null/empty messages,8-bit length truncation, delegated shared-state response. Real source-port zlib/FirmwareBundle/SysexReceiver/SPI/codec/CCL providers;1868 historical native-observation regressions and actual D0/D1/D2 free-order regressions.',limitations=limitations,build_integration=dict(production_partition='Existing TCardFPGAUpdater.cpp membership retained exactly once; Root verifies existing partition and role audit; no shared CMake changed.',public_headers=['presonus/noaa/TCardFPGAUpdater.hpp'],production_sources=['src/Presonus/NOAA/TCardFPGAUpdater.cpp'],test_target='noaa_fpga_programming_replay',test_source='tests/recovery/TCardFPGAProgrammingReplay.cpp',link_targets=['presonus_uc','ZLIB::ZLIB'],link_options=['-Wl,--wrap=inflateInit2_','-Wl,--wrap=inflate','-Wl,--wrap=inflateEnd','-Wl,--wrap=open','-Wl,--wrap=ioctl','-Wl,--wrap=socket'],ctest_name='noaa_fpga_programming_replay',ctest_argv=['uc-library/.venv/bin/python',str(BASE/'check.py'),'replay','--executable','$<TARGET_FILE:noaa_fpga_programming_replay>','--fixtures',str(BASE/'fixtures.json'),'--fixture-sha256',sha(BASE/'fixtures.json')],regression_argv=['uc-library/.venv/bin/python',str(BASE/'check.py'),'regressions'],root_remaining_gates='Root semantic review/local acceptance; fresh canonical Linux/full CTest, role/install/compile-once, active-source proof, declaration-pending guarded SQLite preflight/admission, symbol tracker and mirror audit. No worker readiness ledger changes.'),remarks=str(OUT/'REMARKS.json'),original_declaration_verified=False,original_arm_abi_verified=False,hardware_verified=False)
    write(Path('uc-library/candidates')/task/'HANDOFF.json',handoff)
print('Sealed two exact packet HANDOFF v1 documents with final shared source/provider/format/native/replay hashes')
