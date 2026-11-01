#!/usr/bin/env python3
"""Seal worker-owned artifacts; does not admit readiness or modify shared files."""
import hashlib,json,datetime,subprocess
from pathlib import Path
P=Path('uc-library/candidates/graph-live-trial-05-groups')
SCRATCH=Path('temp/recovery-work/graph-live-trial-05/groups-worker')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def artifact(kind,path):return {'kind':kind,'path':str(path),'sha256':sha(path)}
def main():
 now=datetime.datetime.now(datetime.timezone.utc).isoformat()
 fixtures=json.loads((P/'fixtures.json').read_text())
 replay=json.loads((SCRATCH/'replay-result.json').read_text())
 commands=[json.loads(l) for l in (SCRATCH/'commands.jsonl').read_text().splitlines()]
 (P/'commands.jsonl').write_bytes((SCRATCH/'commands.jsonl').read_bytes())
 (P/'replay-result.json').write_text(json.dumps(replay,indent=2)+'\n')
 sources=['uc-library/include/presonus/surface/GroupsPageComponent.hpp','uc-library/src/Presonus/Surface/GroupsPageComponent.cpp']
 test='uc-library/tests/graph_trial05_groups_tests.cpp'
 providers=['third_party/ccl-framework/core/portable/coreparams.h','third_party/ccl-framework/core/portable/coreparams.cpp','third_party/ccl-framework/core/public/corevector.h']
 common=[artifact('source',s) for s in sources]+[artifact('test',test),artifact('fixture',P/'fixtures.json'),artifact('replay',P/'check.py'),artifact('producer',P/'oracle.py'),artifact('producer',P/'seal.py'),artifact('evidence',P/'commands.jsonl'),artifact('evidence',P/'replay-result.json'),artifact('evidence',P/'work-log.json'),artifact('evidence',P/'README.md')]+[artifact('dependency',s) for s in providers]
 packets=[Path(f'temp/recovery-work/graph-live-trial-05/trial05_groups_{i}-packet') for i in range(1,6)]
 for packet in packets:
  common.append(artifact('packet',packet/'context.json'))
  for n in ['TASK.md','ELF_CONTEXT.md','SOURCE_SLICES.md','CONTEXT.md','SUBAGENT_PROMPT.md','native-context.json']:
   common.append(artifact('dependency',packet/n))
 supplement=Path('evidence/recovery/2026-11-01/dependency-graph/live-trial-05-10x5')
 for path in [supplement/'parameter-vtable-data.json',supplement/'provider-context.json',supplement/'context-expansion-receipts.json',P/'provider-binding.json']:
  common.append(artifact('evidence',path))
 for n in ['03','04','05','06']:
  path=Path(f'temp/recovery-work/graph-live-trial-05/expansions/{n}-groups/expansion.json');common.append(artifact('dependency',path))
 limits=['Portable source contract; original unencoded return declarations unresolved for every target; void/int are intentional port choices.', 'Original class layout, inheritance, ownership, ARM32 ABI and hardware interoperability unverified.', 'refreshList, doselect, observeGroup remain required explicit application hooks; oracle captures call boundary only, not callee semantics.', 'Native named primary AliasParam vtable data establishes slot 0x58 setValue(float,bool) for that table; actual dynamic parameter subclass and whole layout remain unresolved. Actual CCL setter is the source-port contract.', 'Bounded replay uses stable valid arrays/parameter pointers, no callback mutation, null NOBITS error cells; no invalid-pointer/mutating-observer validation.', 'Portable Parameter::setIntValue calls real pinned CCL; native setter body is not executed and provider equivalence is not claimed.']
 domain='Actual original ARM instructions: small count pairs 0..20 for maximum; signed extrema, negative and odd/even requests, old offsets, wrapping addition for offsets; zero through sixteen deselection parameters; negative/first/second/out-of-range selections with prior observed pointers. Compare result, state and ordered boundary arguments; native writes retained.'
 build={'production_partition':'CS18','production_cpp':sources[1],'public_headers':[sources[0]],'test_target':'graph_trial05_groups_tests','test_source':test,'compile_options':['-fno-rtti'],'link_dependencies':['pinned official CCL corelib','presonus_core_allocator'],'ctest_argv':['uc-library/.venv/bin/python',str(P/'check.py'),'replay','--executable','$<TARGET_FILE:graph_trial05_groups_tests>','--fixtures',str(P/'fixtures.json')],'fixtures':[str(P/'fixtures.json')],'shared_files_edited':False}
 proof={'version':1,'utc':now,'scope':'worker-local bounded portable reconstruction, not readiness admission','elf_sha256':fixtures['elf_sha256'],'elf_path':fixtures['elf_path'],'ranges':fixtures['ranges'],'native_execution':{'producer':artifact('producer',P/'oracle.py'),'unicorn_version':fixtures['unicorn_version'],'case_count':len(fixtures['cases']),'boundary_hooks':fixtures['boundary_hooks'],'assumptions':fixtures['assumptions'],'per_target_timing':fixtures['per_target_timing']},'portable_execution':replay,'format_version':subprocess.check_output(['uc-library/.venv/bin/clang-format','--version'],text=True).strip(),'compiler_version':subprocess.check_output(['/usr/bin/c++','--version'],text=True).splitlines()[0],'compiled_symbols':subprocess.check_output(['/usr/bin/nm','--defined-only',str(SCRATCH/'groups.o')],text=True),'commands':commands,'source_hashes':{s:sha(s) for s in sources+[test]},'fixture_hash':sha(P/'fixtures.json'),'upstream':{'commit':'e8cbdea4a4a20e15111f5a690798a259c0374b31','release':'CCL 5.0.0','source_hashes':{s:sha(s) for s in providers},'git_history_verified':True},'limitations':limits,'checks':{'range_bytes':True,'formatted':True,'compiled':True,'exact_mangling':True,'bounded_differential':True,'original_declaration_verified':False,'original_arm_abi_verified':False,'hardware_verified':False}}
 (P/'proof.json').write_text(json.dumps(proof,indent=2)+'\n');common.append(artifact('proof',P/'proof.json'))
 checks=[{'kind':kind,'argv':['uc-library/.venv/bin/python',str(P/'check.py'),kind],'timeout_seconds':120} for kind in ['format','compile','symbols','replay']]
 handoffs=[]
 for i,packet in enumerate(packets,1):
  c=json.loads((packet/'context.json').read_text());o=c['work_binding']['covered_occurrences'][0]
  original={'elf_sha256':o['elf_sha256'],'firmware':'CS18AI surface 13840','role':'client','mangled':o['original_mangled'],'demangled':o['demangled'],'address':o['original_address'],'size':o['original_size'],'section':'.text','section_index':12}
  h={'version':1,'task_id':c['task_id'],'namespace':'Presonus::Surface::GroupsPageComponent','packet_manifest':str(packet/'context.json'),'originals':[original],'artifacts':common,'checks':checks,'validation_domain':domain,'limitations':limits,'build_integration':build}
  d=P/f'packet-{i}';d.mkdir(exist_ok=True);path=d/'HANDOFF.json';path.write_text(json.dumps(h,indent=2)+'\n');handoffs.append({'task_id':c['task_id'],'path':str(path),'sha256':sha(path)})
 (P/'HANDOFF-INDEX.json').write_text(json.dumps({'version':1,'utc':now,'handoffs':handoffs},indent=2)+'\n')
 print(json.dumps(handoffs))
if __name__=='__main__':main()
