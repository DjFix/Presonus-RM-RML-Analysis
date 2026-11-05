#!/usr/bin/env python3
"""Record fresh local checks and per-original handoffs; no admission or global writes."""
import datetime
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import time

BASE = Path('uc-library/candidates/rolling200_02_permissions_readonly')
EVIDENCE = Path('evidence/recovery/2026-11-05/permissions-readonly01')
WORK = Path('temp/recovery-work/permissions-readonly-local01')
PACKETS = Path('temp/recovery-work/rolling200-02/implementation-plan01/packets-current-permissions-readonly04-01/packets')
PRODUCTION = ['uc-library/include/presonus/uc/ClientSubscription.hpp', 'uc-library/include/presonus/mixer/PermissionsComponent.hpp', 'uc-library/src/Presonus/Mixer/PermissionsComponent.cpp']
TEST = 'uc-library/tests/recovery/PermissionsReadonlyReplay.cpp'
PIN = 'e8cbdea4a4a20e15111f5a690798a259c0374b31'

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def artifact(kind, path):
    return dict(kind=kind, path=str(path), sha256=digest(path))

def main():
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    prefix = ['uc-library/.venv/bin/python', str(BASE / 'checks.py')]
    checks = [dict(kind=kind, argv=prefix + [kind], timeout_seconds=120) for kind in ('format', 'compile', 'symbols', 'native', 'replay', 'sanitizers')]
    results = []
    for index, check in enumerate(checks):
        log = EVIDENCE / f'{index:02}-{check["kind"]}.log'
        before = time.monotonic()
        stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with log.open('w') as stream:
            result = subprocess.run(check['argv'], stdout=stream, stderr=subprocess.STDOUT)
        results.append(dict(**check, start_utc=stamp, seconds=time.monotonic()-before, returncode=result.returncode, log=str(log), log_sha256=digest(log)))
        if result.returncode:
            raise RuntimeError(f'{check["kind"]} failed; see {log}')
    deps_argv = ['g++', '-std=c++17', '-Wno-multichar', '-Iuc-library/include', '-Ithird_party/ccl-framework', '-MM', PRODUCTION[2], TEST]
    deps_raw = subprocess.check_output(deps_argv, text=True)
    (EVIDENCE / 'dependencies.d').write_text(deps_raw)
    deps = sorted({s for s in shlex.split(deps_raw.replace('\\\n',' ')) if not s.endswith(':') and Path(s).is_file()})
    providers = []
    upstream = Path('third_party/ccl-framework')
    assert subprocess.check_output(['git', '-C', str(upstream), 'rev-parse', 'HEAD'], text=True).strip() == PIN
    assert subprocess.check_output(['git', '-C', str(upstream), 'rev-list', '--parents', '-n', '1', PIN], text=True).strip() == PIN
    for dep in deps:
        p = Path(dep)
        if p.is_relative_to(upstream):
            original = subprocess.check_output(['git', '-C', str(upstream), 'show', PIN + ':' + str(p.relative_to(upstream))])
            assert hashlib.sha256(original).hexdigest() == digest(p), dep
            providers.append(dict(path=dep, sha256=digest(p), commit=PIN, git_bytes_verified=True))
    (EVIDENCE / 'provider-dependencies.json').write_text(json.dumps(dict(pin=PIN, pinned_root_commit_verified=True, dependencies=providers, argv=deps_argv), indent=2)+'\n')
    native = json.loads((EVIDENCE / 'native-proof.json').read_text())
    limitations = [
        'Original return spellings remain unresolved: int classifications and Core::CStringBuffer<64> aggregate return are intentional provisional source-port choices.',
        'ClientSubscription is a tagged partial source-port value with independent CCL buffers, not original construction, fields/layout, inheritance, virtual interface, ownership or ARM ABI.',
        'Only four exact original ARM getter bodies execute; named libc boundaries are recorded semantic intercept models. No original libc/CCL/hardware execution is claimed. REA tools were unavailable; results are pyelftools/Unicorn observations, not REA Evidence.',
        'Domain requires nonnull createClientInfo input, NUL termination within each 64-byte buffer, safe private memory and no concurrent mutation. Null createClientInfo and malformed strings are excluded.',
        'Local link discards unrelated existing methods with --gc-sections; full Linux integration, existing-method replays, role/install/compile-once checks and readiness remain Root-owned.',
        'Optional sanitizer check excludes vptr: initial generic UBSan link retained RTTI references from unrelated discarded methods. Getters have no virtual call boundary; AddressSanitizer and other UndefinedBehaviorSanitizer checks passed.'
    ]
    domain = dict(native_cases=native['counts'], description='All app/device literal offsets fitting NUL-terminated64-byte buffers; absence, case variants, overlap/precedence; null selected; every display length0..63 with ten device lengths and high-byte samples; compare full64-byte aggregate output including untouched tails, guards and unchanged inputs. Native app PC/write allowlists enforced.')
    remarks = []
    for packet in sorted(PACKETS.iterdir()):
        request = json.loads((packet / 'request.json').read_text())
        target = request['targets'][0]
        remarks.append(dict(date=start, original_elf_sha256=target['original_elf_sha256'], mangled=target['mangled'], unique_work_item=request['work_binding']['work_item_id'], status='compiled_behavior_validated_declaration_pending_not_admitted', owner='/root/isolated_permissions', remarks=limitations, evidence=[str(EVIDENCE/'native-proof.json'),str(EVIDENCE/'local-proof.json')], resolution_or_retry_condition='Native/source evidence establishing actual return declaration is needed before return-declaration promotion; Root must run canonical integration and guarded admission. Preserve original unresolved-provider history; owned explicit source-port values now remove the need for a callback field provider within this domain.'))
    (EVIDENCE / 'remarks.json').write_text(json.dumps(remarks, indent=2)+'\n')
    proof = dict(version=1, session='/root/isolated_permissions', repository=str(Path.cwd()), baseline='7fc9f706110c21b3c80ece4baa87c5fb82dff0dd', branch='codex/rolling200-02-permissions', start_utc=start, end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), checks=results, source_hashes={p:digest(p) for p in PRODUCTION}, test_sha256=digest(TEST), native_proof=artifact('proof', EVIDENCE/'native-proof.json'), dependencies=artifact('proof',EVIDENCE/'provider-dependencies.json'), domain=domain, limitations=limitations, format_before_hashes=True, readiness_admitted=False, hardware_validated=False, original_arm_abi_verified=False, original_declaration_verified=False)
    (EVIDENCE / 'local-proof.json').write_text(json.dumps(proof, indent=2)+'\n')
    artifacts = [artifact('source',p) for p in PRODUCTION] + [artifact('test',TEST)]
    artifacts += [artifact('replay',BASE/'checks.py'),artifact('producer',BASE/'native_oracle.py'),artifact('producer',BASE/'seal.py')]
    for path in sorted(EVIDENCE.iterdir()):
        artifacts.append(artifact('fixture' if path.name=='native-fixture.txt' else 'proof',path))
    for dep in deps:
        if dep not in PRODUCTION + [TEST]:
            artifacts.append(artifact('dependency', dep))
    # Bind all four packets: the selected-app wrapper executes same-owner app body.
    for packet in sorted(PACKETS.iterdir()):
        for name in ('context.json','request.json','TASK.md','CONTEXT.md','SOURCE_SLICES.md','ELF_CONTEXT.md','native-context.json'):
            artifacts.append(artifact('packet', packet/name))
        contract = json.loads((packet/'request.json').read_text())['reconstruction_contract']['path']
        artifacts.append(artifact('contract',contract))
    artifacts.append(artifact('dependency','rootfs/RML16AI_Rack_13731/home/root/mixer'))
    paths = [a['path'] for a in artifacts]
    assert len(paths)==len(set(paths))
    for packet in sorted(PACKETS.iterdir()):
        request = json.loads((packet / 'request.json').read_text())
        original = request['originals'][0]['original']
        native_range = next(r for r in native['ranges'] if r['mangled']==original['mangled'])
        out = BASE/request['task_id']
        out.mkdir(parents=True, exist_ok=True)
        handoff = dict(version=1,task_id=request['task_id'],namespace=request['namespace'],packet_manifest=str(packet/'context.json'),originals=[dict(elf_sha256=original['elf'],firmware=original['firmware'],role=original['role'],mangled=original['mangled'],demangled=original['demangled'],address=original['address'],size=original['size'],section=native_range['section'],section_index=native_range['section_index'],file_offset=native_range['file_offset'],range_sha256=native_range['sha256'])], artifacts=artifacts, checks=checks,validation_domain=domain,limitations=limitations,build_integration=dict(production_partition='Existing PermissionsComponent.cpp remains in its current exactly-one common OBJECT partition; no new production CPP.',public_headers=['uc-library/include/presonus/mixer/PermissionsComponent.hpp','uc-library/include/presonus/uc/ClientSubscription.hpp'],test_target='permissions_readonly_replay',test_source=TEST,link_dependencies='Actual canonical production library and pinned CCL provider. Local bounded check uses actual full-TU object with section garbage collection and libc; no Core test provider.',ctest_argv=['uc-library/.venv/bin/python',str(BASE/'checks.py'),'replay','--executable','<canonical permissions_readonly_replay executable>','--fixture',str(EVIDENCE/'native-fixture.txt')],fixture_binding=artifact('fixture', EVIDENCE/'native-fixture.txt'),source_placement_review='Canonical existing class files plus principal-class ClientSubscription header; no worker/batch production paths.',root_required='Full Linux integration, existing-method behavior replays, role/install/compile-once, active-source proof, guarded SQLite dry-run/admission, tracker/mirror. Worker supplies no readiness fragment or global edits.'))
        (out/'HANDOFF.json').write_text(json.dumps(handoff,indent=2)+'\n')
    print(json.dumps(dict(checks_passed=len(results),native_cases=sum(native['counts'].values()),handoffs=4,ready=False)))

if __name__=='__main__':
    main()
