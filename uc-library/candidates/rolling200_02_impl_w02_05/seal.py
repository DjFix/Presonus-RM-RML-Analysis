#!/usr/bin/env python3
"""Worker local proof and HANDOFF producer; never admits readiness."""
from pathlib import Path
import subprocess, json, hashlib, sys
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[3]
CAND=Path(__file__).resolve().parent
TASK='rolling200_02_impl_w02_05'
OUT=ROOT/'evidence/recovery/2026-11-05/rolling200-02'/TASK
PACKET=ROOT/'temp/recovery-work/rolling200-02/implementation-plan01/packets-batch03/packets'/TASK
PYTHON='uc-library/.venv/bin/python'
sha=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
rel=lambda p: str(p.relative_to(ROOT))
librel=lambda p: str(p.relative_to(ROOT/'uc-library'))
def write(p,value): p.write_text(json.dumps(value,indent=2)+'\n')

def main():
    start=datetime.now(timezone.utc).isoformat()
    checks=[]
    outcomes=[]
    for kind in ('format','compile','symbols','replay'):
        argv=[PYTHON,rel(CAND/'check.py'),kind]
        check={'kind':kind,'argv':argv,'timeout_seconds':120}
        checks.append(check)
        t=datetime.now(timezone.utc).isoformat()
        result=subprocess.run(argv,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        (OUT/(kind+'.log')).write_text(json.dumps(argv)+'\n'+result.stdout)
        outcomes.append(dict(kind=kind,argv=argv,started=t,ended=datetime.now(timezone.utc).isoformat(),returncode=result.returncode,log=rel(OUT/(kind+'.log'))))
        if result.returncode: raise RuntimeError(result.stdout)
    oracle=json.loads((OUT/'native02/arm-oracle.json').read_text())
    req=json.loads((PACKET/'request.json').read_text())
    sourcepaths=[ROOT/p for p in req['owned_files']]+[CAND/'receive_tests.cpp']
    deps=[ROOT/p for p in ['uc-library/src/Presonus/AVB/Protocol.cpp','uc-library/src/Presonus/AVB/Streams.cpp','uc-library/include/presonus/avb/receive_services.hpp','uc-library/include/presonus/avb/streams.hpp','uc-library/include/presonus/dice/sysex.hpp','uc-library/include/presonus/noaa/sysex_packet.hpp','uc-library/include/presonus/dice/packet_services.hpp','uc-library/include/presonus/dice/response_services.hpp','uc-library/include/presonus/dice/sysex_receiver_interface.hpp']]
    corepaths=[ROOT/'third_party/ccl-framework/core/public'/name for name in ['corelinkedlist.h','corecontainer.h','coreplatform.h']]
    corepaths += [ROOT/'third_party/ccl-framework/core/malloc/coremalloc.cpp', ROOT/'third_party/ccl-framework/core/public/coremalloc.h']
    domain='81520 exact server ARM executions: all256length x256command combinations; signed gate edges; valid notifications across all256 identifiers, empty/nonmatching/duplicate-ID ordered lists with first-match behavior; initialized 64-byte scratch/prefix truncation controls; exact helper status/frame, unchanged packet/stream memory, ordered helper/update/notice arguments, notice return/mutation captures. Actual CCL LinkedList and allocator; native receive/unpack/update bodies execute, only notice slots captured at test boundary.'
    limitations=['Original ordinary receive return declaration remains unresolved; void/virtual source declarations are portable choices. Raw native R0 retained but excluded from API comparison.', 'Independent ReceiveContext/packet/stream models do not establish original layout, inheritance, ARM32 ABI or binary compatibility. Borrowed nonnull objects and a valid nonnull NoticeSink are preconditions.', 'Explicit scratch/prefix seeds model initialized memory; no deterministic claim for historical uninitialized stack. No hardware, concurrency, MMIO, notice-provider internal behavior, malformed cyclic lists or null-stream behavior is verified.', 'Adding NOAA virtual overload changes the independent portable vtable. Existing DICE body is unchanged and both mangled definitions are emitted; header-dependent existing proof hashes require Root fresh integration/reseal.']
    function=dict(oracle['functions'][req['targets'][0]['mangled']],original_elf_sha256=oracle['original_elf_sha256'],role='server',firmware='RM/RML mixer 13731')
    proof=dict(version=1,task_id=TASK,status='local validated source port; declaration pending; no global admission',portable_ready=True,cpp_differential_passed=True,compiled_mangled_names_matched=True,cpp_compiled=True,mangling_namespace_checked=True,mangled_names=[function['mangled']],functions=[function],sources={librel(p):sha(p) for p in sourcepaths+deps},repository_sources={rel(p):sha(p) for p in corepaths},domain=domain,validation_domain=domain,unresolved=limitations,formatter='clang-format version 23.1.3',format_check_passed=True,commands=outcomes,native_oracle=dict(path=rel(OUT/'native02/arm-oracle.json'),sha256=sha(OUT/'native02/arm-oracle.json'),producer=rel(CAND/'oracle.py'),producer_sha256=sha(CAND/'oracle.py'),unicorn_version=oracle['unicorn_version'],original_executions=81520,execution_argv=[PYTHON,rel(CAND/'oracle.py'),rel(OUT/'native02')],execution_exit_code=0,producer_python_version=sys.version),portable_executions=81520,fixture=dict(path=rel(OUT/'native02/receive-vectors.txt.gz'),sha256=sha(OUT/'native02/receive-vectors.txt.gz')),replay_producer=dict(path=rel(CAND/'check.py'),sha256=sha(CAND/'check.py')),seal_producer=dict(path=rel(Path(__file__)),sha256=sha(Path(__file__))),started=start,ended=datetime.now(timezone.utc).isoformat(),affected_existing_functions=['Presonus::AVB::AvbManagerBase::receive(const DICE::SysexPacket&)', 'Presonus::AVB::AvbManagerBase::accepts(const DICE::SysexPacket&)', 'Presonus::AVB::AvbManagerBase::unpackAvbSpiMsg(unsigned char*,const unsigned char*,int)', 'Presonus::AVB::AvbManagerBase::reverseEndian(unsigned long long)', 'Presonus::AVB::AvbManagerBase::char2Nibble(const unsigned char*,unsigned char*,int)', 'Presonus::AVB::AvbManagerBase::nibble2Char(const unsigned char*,unsigned char*,int)', 'Presonus::AVB::AvbManagerBase::findListener(unsigned char)', 'Presonus::AVB::AvbManagerBase::findTalker(unsigned char)', 'Presonus::AVB::AvbManagerBase::lookupNextTalkerIndex()'],core_pin=subprocess.check_output(['git','-C','third_party/ccl-framework','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),executable_sha256=sha(ROOT/'temp/recovery-work/rolling200-02'/TASK/'receive-tests'))
    write(CAND/'proof.json',proof)
    entry=dict(role='server',mangled=function['mangled'],original_elf_sha256=function['original_elf_sha256'],cpp_compiled=True,mangling_namespace_checked=True,portable_ready=False,sources=proof['sources'],repository_sources=proof['repository_sources'],validation=librel(CAND/'proof.json'),validation_sha256=sha(CAND/'proof.json'),domain=domain,unresolved=limitations)
    write(CAND/'pending.json',dict(functions=[entry]))
    argv=[PYTHON,'uc-library/tools/merge_readiness.py','--library','uc-library','--pending',librel(CAND/'pending.json'),'--dry-run']
    result=subprocess.run(argv,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (OUT/'readiness-preflight.log').write_text(json.dumps(argv)+'\n'+result.stdout)
    write(OUT/'notes.json',dict(date=datetime.now(timezone.utc).isoformat(),task_id=TASK,original_elf_sha256=function['original_elf_sha256'],mangled=function['mangled'],work_item_id=req['work_binding']['work_item_id'],status='local_validated_declaration_pending',owner='/root/rolling200_02_stage03_w02',remarks=limitations,resolution_or_retry_condition='Root fresh canonical Linux integration/format/current-source reseals, role/install/compile-once and guarded pending admission; declaration promotion requires independent original return evidence.',preflight_returncode=result.returncode,evidence=[rel(CAND/'proof.json'),rel(OUT/'readiness-preflight.log')],readiness_effect='None'))
    artifacts=[]
    def add(kind,p): artifacts.append(dict(kind=kind,path=rel(p),sha256=sha(p)))
    for p in sourcepaths: add('test' if p.name == 'receive_tests.cpp' else 'source',p)
    for p in deps+corepaths: add('dependency',p)
    for p in [CAND/'check.py',CAND/'oracle.py',Path(__file__)]: add('replay' if p.name == 'check.py' else 'producer',p)
    for p in [CAND/'proof.json',CAND/'pending.json',OUT/'native02/arm-oracle.json',OUT/'native02/receive-vectors.txt.gz',OUT/'native02/original-vtable.bin',OUT/'notes.json',OUT/'readiness-preflight.log']+[OUT/(k+'.log') for k in ('format','compile','symbols','replay')]:add('proof' if p.name == 'proof.json' else 'fixture' if p.name == 'receive-vectors.txt.gz' else 'evidence',p)
    for name in ['context.json','TASK.md','CONTEXT.md','SOURCE_SLICES.md','ELF_CONTEXT.md','request.json']:add('packet',PACKET/name)
    add('dependency',ROOT/'temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a')
    add('contract', ROOT/req['reconstruction_contract']['path'])
    elf=ROOT/'rootfs/RML16AI_Rack_13731/home/root/mixer'
    add('original',elf)
    original=req['originals'][0]['original']
    originals=[dict(elf_sha256=original['elf'],firmware=original['firmware'],role=original['role'],mangled=original['mangled'],address=original['address'],size=original['size'],section='.text')]
    integration=dict(production_partition='common (existing AvbManagerReceive.cpp; no new production TU)',public_headers=['uc-library/include/presonus/avb/protocol.hpp'],test_targets=[dict(name='avb_noaa_receive_replay',source=rel(CAND/'receive_tests.cpp'),compile_options=['-std=c++17'],link_libraries=['presonus::uc','ZLIB::ZLIB'],link_options=['-Wl,--wrap='+n for n in ['_ZN8Presonus3AVB14AvbManagerBase15unpackAvbSpiMsgEPhPKhi','_ZN8Presonus3AVB11AvbListener6updateEhhh','_ZN8Presonus3AVB9AvbTalker6updateEhh']],ctest_argv=['<canonical-built-avb_noaa_receive_replay>',rel(OUT/'native02/receive-vectors.txt.gz')])],fixture_bindings={rel(OUT/'native02/receive-vectors.txt.gz'):sha(OUT/'native02/receive-vectors.txt.gz')},dependency_note='Canonical target links actual pinned CCL core/allocator through presonus::uc. Existing DICE receive regression and all header-dependent active proofs require reseal.')
    write(CAND/'HANDOFF.json',dict(version=1,task_id=TASK,namespace=req['namespace'],packet_manifest=rel(PACKET/'context.json'),originals=originals,artifacts=artifacts,checks=checks,validation_domain=domain,limitations=limitations,build_integration=integration))
    print('HANDOFF',rel(CAND/'HANDOFF.json'),'preflight',result.returncode)

if __name__=='__main__': main()
