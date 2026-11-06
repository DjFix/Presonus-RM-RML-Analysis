"""Seal scoped worker evidence; never changes shared integration or readiness."""
import datetime, hashlib, importlib.util, json, os, subprocess, time
from pathlib import Path
from check import ROOT, BASE, FORMAT, SOURCES, OUT
EVIDENCE = Path('evidence/recovery/2026-11-06/rolling200-03/controller173')
PYTHON = 'uc-library/.venv/bin/python'
CHECK = str(BASE/'check.py')
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def artifact(kind, path):
    return dict(kind=kind, path=str(path), sha256=sha(path))
def main():
    os.chdir(ROOT)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    checks = [dict(kind=k, argv=[PYTHON, CHECK, k], timeout_seconds=120) for k in ('format','compile','symbols','native','replay')]
    results = []
    for i, check in enumerate(checks):
        start = time.monotonic(); stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        log = EVIDENCE/f'{i:02d}-{check["kind"]}.log'
        with log.open('w') as stream:
            result = subprocess.run(check['argv'], stdout=stream, stderr=subprocess.STDOUT, timeout=120)
        results.append(dict(**check, returncode=result.returncode, start_utc=stamp, seconds=time.monotonic()-start, log=str(log), log_sha256=sha(log)))
        assert result.returncode == 0, log
    provider = 'temp/core-upstream/root-integration-01/upstream-core/sdk'
    dependencies = set(SOURCES + FORMAT + [str(BASE/p) for p in ('native.py','check.py','seal.py','fixtures.json')])
    # Bind the actual preprocessor closure of every compiled local translation unit.
    deps = subprocess.check_output(['g++','-std=c++20','-MM','-Iuc-library/include','-Ithird_party/ccl-framework','-I'+provider+'/include/presonus-core-5'] + SOURCES, text=True)
    for line in deps.replace('\\\n',' ').splitlines():
        dependencies.update(line.split(':',1)[1].split())
    dependencies.update([provider+'/lib/libcorelib.a',provider+'/lib/libpresonus_core_allocator.a',provider+'/share/presonus-core-5/provenance.json','temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a', 'evidence/recovery/2026-11-06/rolling200-02/fx-closure141/CONTROLLER_RTTI150.json'])
    versions = {name:subprocess.check_output(argv,text=True).splitlines()[0] for name,argv in {'compiler':['g++','--version'],'formatter':['uc-library/.venv/bin/clang-format','--version'],'symbols':['nm','--version']}.items()}
    provider_commit = subprocess.check_output(['git','-C','third_party/ccl-framework','show','-s','--format=%H %P','e8cbdea4a4a20e15111f5a690798a259c0374b31'],text=True).strip()
    assert provider_commit == 'e8cbdea4a4a20e15111f5a690798a259c0374b31'
    fixture = json.loads((BASE/'fixtures.json').read_text())
    domain = '64 initialized Core InterfaceProperty cases: four type IDs (zero, interface, unknown -1, setup), four size words (0,8,24,-1), two iids, null/ordinary borrowed ptr payload, randomized byte patterns. Original ARM bodies independently execute all four instructions for each separate ELF identity; application state/property/payload stay unchanged with stack-only reads/writes and no external calls. Portable replay uses typed Core/IController routes, complete state and payload snapshots, actual existing Controller property/setup/flush/normalization/info/format/scan/send/default/release/destructor methods and real pinned CCL Property, GetInterface, LinearInterpolator, vector, formatter registry and allocator providers.'
    limitations = ['Portable source port; no ARM32 layout, vtable slot offset, calling convention, binary interoperability or hardware verification.', 'getProperty void follows actual pinned IPropertyHandler; original ordinary return declaration remains independently unresolved. processIdle void is an explicit source contract, not recovered original return evidence.', 'Original stack housekeeping writes are recorded, not reproduced by portable application semantics. Original r0 is not interpreted as a return.', 'Only two assigned original identities receive native behavior evidence. Existing Controller/provider routes are preservation/source-provider integration tests; source-model parameter storage and doUpdates live only in the legitimate concrete test subclass.', 'Core binary recovery, DspComponent/FX implementations, production shared build integration, full Linux CTest and readiness admission remain outside worker ownership.']
    proof = dict(version=1, created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), session_id=os.environ.get('CODEX_THREAD_ID','unavailable-to-worker'), worker='rolling200_03_controller173', elf_sha256=fixture['elf_sha256'], elf_path='rootfs/RML16AI_Rack_13731/home/root/mixer', native_ranges=[{k:v for k,v in r.items() if k!='observations'} for r in fixture['ranges']], original_executions=128, portable_fixture_cases=64, checks=results, versions=versions, provider_commit=provider_commit, oracle_producer=artifact('producer',BASE/'native.py'), replay_producer=artifact('producer',BASE/'check.py'), dependencies=[artifact('dependency',p) for p in sorted(dependencies)], fixture=artifact('fixture',BASE/'fixtures.json'), executable=artifact('compiled',OUT/'replay'), symbols=artifact('symbols',OUT/'symbols.txt'), validation_domain=domain, limitations=limitations, readiness_admitted=False)
    proof_path = EVIDENCE/'PROOF.json';proof_path.write_text(json.dumps(proof,indent=2)+'\n')
    for number in (1,2):
        task = f'rolling200_03_controller173_0{number}'
        packet = Path('temp/recovery-work/rolling200-03/controller173/prepared173/packets')/task
        request = json.loads((packet/'request.json').read_text())
        original = request['originals'][0]['original']
        manifest = packet/'context.json'
        artifacts = []
        for p in sorted(dependencies):
            if p in FORMAT or p in SOURCES: kind = 'test' if p.endswith('ControllerInterfaceReplay.cpp') else 'source'
            elif p == str(BASE/'fixtures.json'): kind='fixture'
            elif p == str(BASE/'check.py'): kind='replay'
            else: kind='dependency'
            artifacts.append(artifact(kind,p))
        artifacts += [artifact('proof',proof_path),artifact('packet',manifest),artifact('contract',request['reconstruction_contract']['path'])]
        artifacts += [artifact('packet',packet/name) for name in ('request.json','TASK.md','ELF_CONTEXT.md','SOURCE_SLICES.md','CONTEXT.md')]
        artifacts += [artifact('log',r['log']) for r in results]
        handoff = dict(version=1,task_id=task,namespace='Presonus::Dsp',packet_manifest=str(manifest),originals=[dict(elf_sha256=original['elf'],firmware=original['firmware'],role=original['role'],mangled=original['mangled'],address=original['address'],size=original['size'],section=int(original['section_json']))],artifacts=artifacts,checks=checks,validation_domain=domain,limitations=limitations,build_integration=dict(production_partition='common: add src/Presonus/Dsp/ControllerInterface.cpp exactly once',public_headers=['include/presonus/dsp/IController.hpp','include/presonus/dsp/Controller.hpp'],test_target='controller_interface_replay: tests/recovery/ControllerInterfaceReplay.cpp linked to presonus_uc and pinned Core provider',ctest_argv=[PYTHON,CHECK,'replay',str(BASE/'fixtures.json'),'<TARGET_FILE:controller_interface_replay>'],fixture=str(BASE/'fixtures.json'),link_dependencies=['presonus_uc','actual pinned CCL corelib/allocator'],root_required='Recompile all Controller-dependent TUs, rebind affected active-source proofs, full Linux CTest and role/installed/compile-once audits before guarded readiness admission. No worker admission.'),remarks=dict(unique_work_item=request['existing_work_item_id'],status='compiled-pending-original-declarations',resolution='Original return declarations require independent declaration evidence; source-port ancestry is supported by original RTTI, not layout.'))
        destination=Path('uc-library/candidates')/task/'HANDOFF.json';destination.parent.mkdir(parents=True,exist_ok=True);destination.write_text(json.dumps(handoff,indent=2)+'\n')
        spec=importlib.util.spec_from_file_location('accept_worker','uc-library/tools/recovery/accept_worker.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        module.validate(handoff)
        print('stock accept_worker.validate passed:',destination)
if __name__ == '__main__': main()
