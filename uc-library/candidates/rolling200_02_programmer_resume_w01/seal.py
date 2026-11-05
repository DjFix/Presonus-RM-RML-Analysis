"""Seal local worker evidence; never changes readiness or shared build files."""
import datetime
import hashlib
import importlib.metadata
import json
import subprocess
from pathlib import Path

B=Path('uc-library/candidates/rolling200_02_programmer_resume_w01')
E=Path('evidence/recovery/2026-11-05/rolling200-02/programmer-resume-w01')
S=Path('temp/recovery-work/rolling200-02/programmer-resume-w01')
P=Path('temp/recovery-work/rolling200-02/programmer-resume01/packets-batch01/packets')
SOURCE=Path('uc-library/src/Presonus/NOAA/TCardProgrammerUpdate.cpp')

def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(argv):
    start=datetime.datetime.now(datetime.timezone.utc)
    result=subprocess.run(argv,text=True,capture_output=True)
    record={'argv':argv,'start_utc':start.isoformat(),'end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
    if result.returncode: raise RuntimeError(record)
    return record

def main():
    E.mkdir(parents=True,exist_ok=True)
    native=json.loads((E/'native.json').read_text())
    checks=[{'kind':'format','argv':['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',str(SOURCE),str(B/'replay.cpp')],'timeout_seconds':120}, {'kind':'compile','argv':['uc-library/.venv/bin/python',str(B/'checks.py'),'compile'],'timeout_seconds':120},{'kind':'symbols','argv':['uc-library/.venv/bin/python',str(B/'checks.py'),'symbols'],'timeout_seconds':120},{'kind':'replay','argv':['uc-library/.venv/bin/python',str(B/'replay.py'),str(S/'replay'),str(E/'native.json')],'timeout_seconds':120}]
    checks.append({'kind':'replay','argv':['uc-library/.venv/bin/python',str(B/'replay.py'),str(S/'replay'),str(E/'epoch-audit.json')],'timeout_seconds':120})
    results=[run(c['argv']) for c in checks]
    audit=json.loads((E/'epoch-audit.json').read_text())
    assert len(audit['cases']) == 6
    assert all(c['epoch_address']==0x4953b0 and c['epoch_memory']=='87d6120000000000' for c in audit['cases'])
    versions=[run(['uc-library/.venv/bin/clang-format','--version']),run(['g++','--version']),run(['nm','--version']),run(['git','-C','third_party/ccl-framework','rev-parse','HEAD']),run(['git','-C','third_party/ccl-framework','rev-list','--max-parents=0','HEAD'])]
    deps=[Path('uc-library/include/presonus/noaa/programmer.hpp'),Path('third_party/ccl-framework/core/public/corestringbuffer.h'),Path('third_party/ccl-framework/core/public/corestringtraits.h'),Path('third_party/ccl-framework/core/public/coretypes.h')]
    limitations=['Portable source port only. Original ordinary return declarations, class layout and ARM ABI remain unresolved; declaration-pending, not ready.', 'Native executes exactly four approved original ARM ranges. All serial/protocol/print/Core/libgcc entries are scripted test boundaries; intercepted providers are not independently validated here.', 'No hardware/device/network/serial/ioctl/syscall forwarding. No lifecycle, real clock/debug, exceptional cleanup or original binary interoperability claims.', 'Image pointer assumed valid for bounded length; lengths limited to 0,1,2,255,256,257,512. Scripted command/ACK outcomes only 0/1. sendAddress/sendPacket/writeChar failures and arbitrary provider state changes excluded.']
    domains={}
    for target in native['targets']:
        method=target['demangled'].split('::')[-1].split('(')[0]
        cases=[c for c in native['cases'] if c['method']==method]
        domains[target['mangled']]={'case_count':len(cases),'lengths':sorted({c['length'] for c in cases}),'initial_cancel':[0,1],'failure_index':list(range(-1,10)),'additional_cases':'writeImage/update: cancellation after first completed chunk and ACK count-byte overwrite; high-level nested methods execute actual approved ranges','observed':['return','ordered provider calls and payload bytes','progress/debug messages','257-byte outbound memory','cancellation byte','application PC counts','boundary-entry counts']}
    proof={'version':1,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'worker_session':'/root/rolling200_02_programmer_resume_w01','native_execution':{'argv':['uc-library/.venv/bin/python',str(B/'oracle.py')],'started_utc':'2026-11-05T08:13:54+00:00','process_id':1755458,'tool_session':69096,'elf_sha256':native['elf_sha256'],'ranges':native['targets'],'negative_guards':native['negative_guard_checks'],'fixture':{'path':str(E/'native.json'),'sha256':digest(E/'native.json')},'oracle':{'path':str(B/'oracle.py'),'sha256':digest(B/'oracle.py')},'unicorn_version':importlib.metadata.version('unicorn'),'scope':'independent original ARM instruction execution; scripted provider boundaries'},'portable_checks':results,'versions':versions,'validation_domains':domains,'limitations':limitations,'source_hashes':{str(p):digest(p) for p in [SOURCE,B/'replay.cpp',B/'replay.py',B/'checks.py',B/'oracle.py',*deps]},'affected_existing_functions':[],'core_dependencies':[str(p) for p in deps if str(p).startswith('third_party/')],'root_review':'evidence/recovery/2026-11-05/rolling200-02/PROGRAMMER_ORACLE_ROOT_REVIEW02.json'}
    proof['native_execution']['returncode']=0
    proof['native_execution']['completed_utc']=datetime.datetime.fromtimestamp((E/'native.json').stat().st_mtime,datetime.timezone.utc).isoformat()
    proof['native_execution']['observed_case_count']=len(native['cases'])
    proof['native_execution']['negative_guard_checks_passed']=len(native['negative_guard_checks'])==4
    proof['epoch_audit']={'fixture':str(E/'epoch-audit.json'),'fixture_sha256':digest(E/'epoch-audit.json'),'producer':str(B/'epoch_audit.py'),'producer_sha256':digest(B/'epoch_audit.py'),'argv':['uc-library/.venv/bin/python',str(B/'epoch_audit.py')],'review':'evidence/recovery/2026-11-05/rolling200-02/PROGRAMMER_EPOCH_ROOT_REVIEW01.json','case_count':6,'returncode':0,'completed_utc':datetime.datetime.fromtimestamp((E/'epoch-audit.json').stat().st_mtime,datetime.timezone.utc).isoformat(),'native_address':0x4953b0,'native_bytes':'87d6120000000000','native_value':1234567,'portable_setter_comparison':'actual stored value captured by test bridge and compared by replay.py to native epoch bytes'}
    (E/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    (E/'remarks.json').write_text(json.dumps({'date':proof['utc'],'owner':proof['worker_session'],'notes':[{'elf_sha256':native['elf_sha256'],'mangled':t['mangled'],'work_item_id':json.loads((Path(t['packet'])/'request.json').read_text())['work_binding']['work_item_id'],'status':'locally_validated_declaration_pending','observation':'Preserved implementation independently matches approved memory-only native oracle at scripted high-level boundaries. Earlier auto-review execution blocker resolved by explicit scoped user approval; historical rejection retained.','bounded_domain':domains[t['mangled']],'resolution_or_retry_condition':'Original ordinary return declarations need independent declaration evidence; full Root integration/admission remains required. Additional provider/invalid-pointer domains require new independently bound observations.','evidence':[str(E/'native.json'),str(E/'proof.json')]} for t in native['targets']]},indent=2)+'\n')
    common=[('source',SOURCE),('test',B/'replay.cpp'),('replay',B/'replay.py'),('producer',B/'checks.py'),('producer',B/'oracle.py'),('producer',B/'seal.py'),('fixture',E/'native.json'),('proof',E/'proof.json'),('remarks',E/'remarks.json'),('boundary',B/'ORACLE_BOUNDARY.json'),('review',Path(proof['root_review'])),('authorization',Path('evidence/recovery/2026-11-05/rolling200-02/programmer-emulation-approval01/AUTHORIZATION.json'))]+[('dependency',p) for p in deps]
    common += [('fixture',E/'epoch-audit.json'),('producer',B/'epoch_audit.py'),('boundary',B/'EPOCH_AUDIT_BOUNDARY.json'),('review',Path(proof['epoch_audit']['review']))]
    for target in native['targets']:
        packet=Path(target['packet']); request=json.loads((packet/'request.json').read_text()); task=request['task_id']; destination=B/task;destination.mkdir(exist_ok=True)
        artifact_paths=common+[('packet',packet/'context.json'),('task',packet/'request.json'),('native_context',packet/'native-context.json'),('contract',Path(request['reconstruction_contract']['path']))]
        handoff={'version':1,'task_id':task,'namespace':'Presonus::NOAA::TCardProgrammer','packet_manifest':str(packet/'context.json'),'originals':[{'elf_sha256':target['elf'],'firmware':target['firmware'],'role':target['role'],'mangled':target['mangled'],'address':target['address'],'size':target['size'],'section':'.text'}],'artifacts':[{'kind':kind,'path':str(p),'sha256':digest(p)} for kind,p in artifact_paths],'checks':checks,'validation_domain':domains[target['mangled']],'limitations':limitations,'build_integration':{'production_partition':'RM exclusive: verify original ownership and add exactly once to RM OBJECT partition','public_headers':['uc-library/include/presonus/noaa/programmer.hpp'],'test_targets':['noaa_programmer_update_boundary_replay'],'test_source':str(B/'replay.cpp'),'link_dependencies':['canonical RM production archive with actual update TU; test-only dependency definitions satisfy intercepted boundaries','pinned CCL headers'],'replay_argv':['uc-library/.venv/bin/python',str(B/'replay.py'),'CANONICAL_BUILT_EXECUTABLE',str(E/'native.json')],'ctest_argv':['uc-library/.venv/bin/ctest','--test-dir','temp/core-upstream/root-integration-01','-R','noaa_programmer_update_boundary_replay','--output-on-failure'],'fixture_bindings':[{'path':str(E/'native.json'),'sha256':digest(E/'native.json')},{'path':str(E/'epoch-audit.json'),'sha256':digest(E/'epoch-audit.json')}]}}
        (destination/'HANDOFF.json').write_text(json.dumps(handoff,indent=2)+'\n')
    print(json.dumps({'status':'sealed','case_count':len(native['cases']),'handoffs':4,'proof':str(E/'proof.json')}))

if __name__=='__main__': main()
