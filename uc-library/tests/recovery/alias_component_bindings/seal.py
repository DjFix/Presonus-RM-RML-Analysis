"""Run local gates and write five identity-specific HANDOFF v1 deliveries."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'evidence/recovery/2026-11-06/rolling200-03/alias-component-bindings'
BASE='temp/recovery-work/rolling200-03/alias01/prepared01/packets'
REPLAY='uc-library/tests/recovery/alias_component_bindings/check.py'
PROOF=str((OUT/'proof.json').relative_to(ROOT))
SOURCES=['uc-library/include/presonus/AliasComponent.hpp','uc-library/src/Presonus/AliasComponent.cpp']
TEST='uc-library/tests/recovery/AliasComponentBindingsReplay.cpp'
FIXTURE='uc-library/tests/recovery/alias_component_bindings/fixtures.json'
ORACLE='uc-library/tests/recovery/alias_component_bindings/native.py'
PRODUCER='uc-library/tests/recovery/alias_component_bindings/seal.py'
PROVIDERS=['third_party/ccl-framework/core/portable/corecomponent.h','third_party/ccl-framework/core/portable/corecomponent.cpp','third_party/ccl-framework/core/portable/coreparams.h','third_party/ccl-framework/core/portable/coreparams.cpp','third_party/ccl-framework/core/portable/coreparaminfo.h']
def digest(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def artifact(kind,p):return dict(kind=kind,path=p,sha256=digest(p))
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    checks=[dict(kind=k,argv=['uc-library/.venv/bin/python',REPLAY,k],timeout_seconds=120) for k in ('format','compile','symbols','replay')]
    results=[]
    for c in checks:
        start=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic()
        r=subprocess.run(c['argv'],cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        log=OUT/(c['kind']+'.log');log.write_text(r.stdout)
        results.append(dict(**c,start_utc=start,seconds=time.monotonic()-t,returncode=r.returncode,log=str(log.relative_to(ROOT)),log_sha256=digest(str(log.relative_to(ROOT)))))
        if r.returncode:raise RuntimeError(r.stdout)
    fixtures=json.loads((ROOT/FIXTURE).read_text())
    limitation=fixtures['limitations']+[
        'Portable CCL source port only. Original class fields, complete declarations, ownership, layout and ARM ABI remain unverified. getOriginal pointer and setOriginal void are source-port contracts, not proven original return declarations.',
        'Source-port ParamInfo uses actual pinned CCL owned copy, zero initialization, bounded 31-character name; malformed unterminated source names throw length_error instead of native unbounded strcpy.',
        'Silent provider vector insertion failure converted to bad_alloc while retaining ownership. CCL internal storable/public counters on silent allocation failure are provider behavior, not repaired here.',
        'Test-only global C++ allocator fault injection does not replace any production Core methods. Provider malloc/realloc failure and allocator-personality behavior are not claimed.',
        'Original null parameter slots tested only through bounded native interfaces; actual nonvirtual CCL collection public API does not support sparse null elements.',
        'Borrowed component pointer can dangle after referent destruction; actual AliasParam observes parameter destruction, but this does not establish component lifetime ownership. Self aliasing and reentrant collection mutation excluded.',
        'Original name-only constructor/destructors reused; no extra reconstruction credit. No hardware, syscalls, firmware updates, ARM provider execution or binary interoperability tested.'
    ]
    domain='14 original app ARM executions: null, empty, bind, same, replacement, clear, preserve, sparse, C1, C2, delegation and three injected cleanup paths; nine host/provider snapshot comparisons; 32 constructor and 16 partial-rebind fault positions; actual CCL observer, enabled state, order/tag/name, owned info, controller, borrowed lifetime and paramChanged dirty-state checks.'
    proof=dict(version=1,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),session_id=os.environ.get('CODEX_THREAD_ID','/root/rolling200_03_alias01'),checkout=str(ROOT),base_commit='8c13ac41cc6a48dfec1d12d29ca665ab02ba027e',elf_sha256=fixtures['elf_sha256'],ranges=fixtures['ranges'],native_case_count=len(fixtures['cases']),differential_case_count=9,unicorn_version=fixtures['unicorn_version'],formatter_version=subprocess.check_output(['uc-library/.venv/bin/clang-format','--version'],cwd=ROOT,text=True).strip(),compiler_version=subprocess.check_output(['/usr/bin/c++','--version'],text=True).splitlines()[0],source_hashes={p:digest(p) for p in SOURCES+[TEST,ORACLE,REPLAY,FIXTURE,PRODUCER]+PROVIDERS},commands=results,validation_domain=domain,limitations=limitation,local_checks_passed=True,readiness_admitted=False,source_port_only=True)
    (OUT/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    # Durable reconstruction remarks, bound to each exact original identity.
    notes=[]
    for p in sorted((ROOT/BASE).iterdir()):
        req=json.loads((p/'request.json').read_text());o=req['originals'][0]['original']
        manifest=str((p/'context.json').relative_to(ROOT))
        originals=[dict(elf_sha256=o['elf'],firmware=o['firmware'],role=o['role'],mangled=o['mangled'],address=o['address'],size=o['size'],section='.text')]
        artifacts=[artifact('source',s) for s in SOURCES]+[artifact('test',TEST),artifact('fixture',FIXTURE),artifact('replay',REPLAY),artifact('oracle',ORACLE),artifact('producer',PRODUCER),artifact('proof',PROOF),artifact('packet',manifest),artifact('native_evidence','evidence/recovery/2026-11-06/rolling200-03/alias-component/VIRTUAL_SLOTS01.json')]+[artifact('provider',s) for s in PROVIDERS]
        for s in ('temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a'):
            artifacts.append(artifact('provider_archive',s))
        handoff=dict(version=1,task_id=req['task_id'],namespace='Presonus',packet_manifest=manifest,originals=originals,artifacts=artifacts,checks=checks,validation_domain=domain,limitations=limitation,build_integration=dict(production_partition='existing common AliasComponent.cpp partition; no new production CPP',public_headers=SOURCES[:1],test_target='alias_component_bindings_replay',test_sources=[TEST],link_dependencies=['presonus_uc','actual pinned CCL provider'],test_allocator='The replay defines test-only fault-injection global new/delete; do not link another overriding allocator in this target.',ctest_argv=['uc-library/.venv/bin/python',REPLAY,'replay','--executable','$<TARGET_FILE:alias_component_bindings_replay>'],fixtures=[FIXTURE],note='Root owns all CMake, global tests, role/install/compile-once audits and guarded registry admission.'))
        dest=ROOT/'uc-library/candidates'/req['task_id']/'HANDOFF.json';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(handoff,indent=2)+'\n')
        notes.append(dict(date=proof['created_utc'],status='local-validated-awaiting-root-integration',original=originals[0],unique_work_item=req['work_binding']['work_item_id'],proof=PROOF,remarks=limitation,retry_condition='Original declarations need independent evidence; all original ABI/hardware claims remain excluded. Source changes require fresh replay/proof.'))
    (OUT/'remarks.json').write_text(json.dumps(notes,indent=2)+'\n')
    print(json.dumps(dict(proof=PROOF,handoffs=5,checks_passed=True)))
if __name__=='__main__':main()
