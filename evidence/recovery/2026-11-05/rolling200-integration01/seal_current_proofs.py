"""Seal this production integration; preserve per-symbol domains and old proofs."""
from pathlib import Path
import copy, hashlib, json, re, subprocess, sys
from elftools.elf.elffile import ELFFile
R=Path.cwd();L=R/'uc-library';E=R/'evidence/recovery/2026-11-05/rolling200-integration01';B=R/'temp/core-upstream/root-integration-01';W=R/'temp/recovery-work/rolling200-implementation01';O=L/'validation/rolling200-production01'
sys.path[:0]=[str(L/'tools'),str(L/'tools/registry')]
from merge_readiness import ValidationCache, repository_sources_match
from adapter import snapshot
c=ValidationCache();sha=c.sha;read=c.read_json
completed=read(E/'linux02/COMPLETED.json');assert completed['passed'] and completed['test_suites']==472
integration=read(L/'validation/integration.json');assert integration==read(L/'validation/integration-linux.json') and integration['ctest_passed'] and integration['test_suites']==472
for p,h in integration['files'].items():assert sha(L/p)==h,p
fmt=read(L/'validation/formatting.json');assert fmt['format_check_passed']
freeze=read(E/'HANDOFF_INPUTS01.json');transition=read(E/'POST_LINUX_INPUT_AUDIT02.json');assert transition['passed']
for p,h in freeze['files'].items():
 if p==transition['generated_input_transition']['original_path']:
  assert sha(R/transition['generated_input_transition']['historical_archive'])==h
  assert sha(R/p)==transition['generated_input_transition']['current_sha256']
 else:assert sha(R/p)==h,p
passed=set(re.findall(r'Test\s+#\d+:\s+(\S+)\s+\.{2,}\s+Passed',(E/'linux02/tests.log').read_text()));assert len(passed)==472
role=json.loads((E/'linux02/role-audit.log').read_text().splitlines()[-1]);assert role['passed'] and role['units']==455
installed=read(E/'linux02/installed-audit.json');assert all(installed[k] for k in ['header_set_matches','compiled_mangles_matched','provider_sdk_matches'])
assert subprocess.check_output(['git','-C',str(R/'third_party/ccl-framework'),'rev-parse','HEAD'],text=True).strip()=='e8cbdea4a4a20e15111f5a690798a259c0374b31'
drift=read(E/'DRIFT01.json');assert drift['counts']=={'pending':129}
with snapshot(L) as current:
 assert current.guard==drift['registry_guard'];existing={(r['original_elf_sha256'],r['mangled']) for status in ['ready','pending'] for r in current.iter_records(status)}
O.mkdir(exist_ok=True);assert not (O/'new.pending-proof.json').exists() and not (O/'existing.pending-proof.json').exists()
archives={};symbols={}
for name in ['presonus_uc','presonus_cs18_components','presonus_rm_components']:
 p=B/('lib'+name+'.a');output=subprocess.check_output(['nm','--defined-only',str(p)],text=True);log=O/(name+'-nm.log');log.write_text(output);symbols[name]={line.split()[-1] for line in output.splitlines() if line.split()};archives[name]={'path':str(p.relative_to(R)),'sha256':sha(p),'symbol_log':str(log.relative_to(L)),'symbol_log_sha256':sha(log)}
elfpaths={'304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0':R/'rootfs/CS18_v13840/home/root/surface','9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07':R/'rootfs/RML16AI_Rack_13731/home/root/mixer'}
def original_range(elfhash,mangled,address=None,size=None):
 path=elfpaths[elfhash];assert sha(path)==elfhash
 with path.open('rb') as stream:
  elf=ELFFile(stream);matches=[s for s in elf.get_section_by_name('.symtab').get_symbol_by_name(mangled) or [] if isinstance(s['st_shndx'],int) and s['st_size']>0 and (address is None or s['st_value']==address) and (size is None or s['st_size']==size)]
  assert len(matches)==1,(mangled,len(matches));s=matches[0];sec=elf.get_section(s['st_shndx']);a=s['st_value'];n=s['st_size'];assert sec['sh_type']!='SHT_NOBITS' and sec['sh_addr']<=a and a+n<=sec['sh_addr']+sec['sh_size'];off=sec['sh_offset']+a-sec['sh_addr'];stream.seek(off);body=stream.read(n);assert len(body)==n
 return {'elf_sha256':elfhash,'mangled':mangled,'address':a,'size':n,'section':sec.name,'section_index':s['st_shndx'],'file_offset':off,'bytes_sha256':hashlib.sha256(body).hexdigest()}
def check_names(elfhash,name):
 target='presonus_cs18_components' if elfhash.startswith('304c') else 'presonus_rm_components';assert name in symbols[target] and name in symbols['presonus_uc'],name

def source_bindings(paths):
 result={}
 for p in sorted(set(paths)):
  f=L/p;h=sha(f)
  if f.suffix in ('.cpp','.hpp','.h'):assert fmt['files'].get(p)==h,p
  result[p]=h
 return result
accepts={}
for p in W.glob('accept*/acceptance.json'):
 a=read(p)
 if a.get('local_acceptance_passed'):accepts[(a['task_id'],a['handoff_sha256'])]={'path':str(p.relative_to(R)),'sha256':sha(p)}
tests={'c08':['recovery_controller_info'],'c12':['panel_element_replay_'+str(i).zfill(2) for i in range(1,11)],'c14':['sl_channel_base_replay'],'c15':['mappable_mixer_replay'],'c17':['preset_cache_info_replay'],'c22':['messenger_lifecycle_replay'],'c24':['shared_memory_comm_replay'],'c10':['rolling200_controls01_native','rolling200_controls01_attributes','rolling200_controls01_provider_lifecycle'],'c11':['rolling200_controls01_native','rolling200_controls01_attributes','rolling200_controls01_provider_lifecycle']}
newrows=[];newfunctions=[];remarks=[]
for ref in freeze['handoffs']:
 hp=R/ref['path'];assert sha(hp)==ref['sha256'];h=read(hp);task=h['task_id'];assert (task,ref['sha256']) in accepts
 packet=read(R/h['packet_manifest']);request=read((R/h['packet_manifest']).parent/'request.json');group=task.split('_')[2];assert set(tests[group])<=passed
 sources=source_bindings(str(Path(a['path']).relative_to('uc-library')) for a in h['artifacts'] if a['kind'] in ('source','test') and a['path'].startswith('uc-library/'))
 assert sources
 providers={p:v for p,v in packet['selected_file_sha256'].items() if p.startswith('third_party/ccl-framework/core/')};assert repository_sources_match(L,{'repository_sources':providers},c)
 native_refs=[a for a in h['artifacts'] if a['kind'] in ('native','oracle','proof','fixture','producer','replay','evidence')]
 domain=h['validation_domain'];domain=domain if isinstance(domain,str) else json.dumps(domain,sort_keys=True)
 limitations=h['limitations'];limitations=limitations if isinstance(limitations,list) else [limitations]
 domain+=' Canonical current Linux build, exact role-archive symbols, bounded native/provider replay and installed-role/compile-once checks passed. Native boundary stubs and independently executed pinned provider behavior retain the handoff limitations; no whole-original-function, original ARM ABI, hardware or declaration-ready claim.'
 for item in request['originals']:
  original=item['original'];key=(original['elf'],original['mangled']);assert key not in existing
  assert any(x['elf_sha256']==key[0] and x['mangled']==key[1] and x['address']==original['address'] and x['size']==original['size'] for x in h['originals'])
  rng=original_range(*key,original['address'],original['size']);check_names(*key)
  row={'original_elf_sha256':key[0],'mangled':key[1],'demangled':original['demangled'],'firmware_version':original['firmware'],'role':original['role'],'original_address':rng['address'],'original_size':rng['size'],'address':rng['address'],'size':rng['size'],'section':rng['section_index'],'sha256':rng['bytes_sha256'],'portable_ready':False,'cpp_compiled':True,'mangling_namespace_checked':True,'original_function_verified':False,'hardware_verified':False,'original_arm_abi_verified':False,'original_declaration_verified':False,'arm_differential_verified':False,'domain':domain,'validation_domain':domain,'unresolved':limitations,'sources':sources,'repository_sources':providers,'work_item_id':request['work_binding']['work_item_id']}
  note={'original_elf_sha256':key[0],'mangled':key[1],'work_item_id':row['work_item_id'],'status':'compiled_declaration_pending','owner':task,'domain':domain,'limitations':limitations,'remarks':h.get('remarks',[]),'handoff':ref,'acceptance':accepts[(task,ref['sha256'])],'retry_condition':'Obtain independent original declarations/member/lifecycle evidence for the unresolved requirements in this exact handoff. Ordinary return inference from a constant/pointer result is insufficient; constructors retain source-port/member/provider limitations. No automatic ready promotion.'};remarks.append(note)
  newfunctions.append(dict(row,native_range=rng,handoff=ref,local_acceptance=accepts[(task,ref['sha256'])],native_provider_evidence=native_refs,canonical_tests=tests[group],promotion_requirements=note['retry_condition']));newrows.append(row)
assert len(newrows)==48 and len({(r['original_elf_sha256'],r['mangled']) for r in newrows})==48
oldrows=[];oldfunctions=[]
for item in drift['affected']:
 assert item['status']=='pending' and item['historical_proof_unchanged'] and item['repository_sources_unchanged']
 row=copy.deepcopy(item['entry']);previous={'path':row['validation'],'sha256':row['validation_sha256']};assert sha(L/previous['path'])==previous['sha256'];oldkey=(row['original_elf_sha256'],row['mangled']);rng=original_range(*oldkey,row.get('original_address'),row.get('original_size'));check_names(*oldkey)
 for change in item['changes']:assert sha(L/change['path'])==change['current_sha256']
 row['sources']=source_bindings(row['sources']);assert repository_sources_match(L,row,c)
 domain=row.get('domain',row.get('validation_domain',''))+' Current integration compatibility after canonical class extensions: all453 prior suites and19 new suites replayed on final source. Existing original uncertainty/native/provider bounds remain; new member/source-port behavior is documented in linked handoffs. This is neither a source move nor an assertion of unchanged binary layout or universal semantic equivalence. No new reconstruction or classification credit for this existing identity.'
 row.update(previous_validation=previous,domain=domain,validation_domain=domain,portable_ready=False,cpp_compiled=True,mangling_namespace_checked=True)
 oldfunctions.append({'original_elf_sha256':oldkey[0],'mangled':oldkey[1],'validation_domain':domain,'sources':row['sources'],'repository_sources':row.get('repository_sources',{}),'previous_validation':previous,'changes':item['changes'],'native_range':rng,'classification_change':False});oldrows.append(row)
assert len(oldrows)==129
(E/'RECONSTRUCTION_REMARKS01.json').write_text(json.dumps({'version':1,'functions':remarks,'notes_do_not_establish_readiness':True},indent=2)+'\n')
common={'version':1,'passed':True,'cpp_compiled':True,'compiled_mangled_names_matched':True,'mangling_namespace_checked':True,'portable_ready':False,'active_source_replay_passed':True,'source_guard_passed':True,'hardware_verified':False,'original_arm_abi_verified':False,'original_declaration_verified':False,'canonical_integration_sha256':sha(L/'validation/integration.json'),'canonical_ctest_suites':472,'formatting_sha256':sha(L/'validation/formatting.json'),'formatter_version':fmt['formatter'],'archives':archives,'role_audit':role,'full_linux_completion':{'path':str((E/'linux02/COMPLETED.json').relative_to(R)),'sha256':sha(E/'linux02/COMPLETED.json')},'historical_build_input_transition':transition,'producer':{'path':str(Path(__file__).relative_to(R)),'sha256':sha(Path(__file__))}}
for kind,rows,functions in [('new',newrows,newfunctions),('existing',oldrows,oldfunctions)]:
 proof=dict(common,functions=functions,new_reconstructed_elf_identities=48 if kind=='new' else 0,bounded_cpp_replay_passed=True,scope='Per-function bounded native application observations and independently executed actual pinned provider/source-port replay; declaration-pending only.' if kind=='new' else 'Fresh source/compile/role/current bounded regression compatibility for existing pending records; prior proof provenance and classifications preserved, no new original-native behavior credit.')
 pp=O/(kind+'.pending-proof.json');pp.write_text(json.dumps(proof,indent=2)+'\n')
 for row in rows:row.update(validation=str(pp.relative_to(L)),validation_sha256=sha(pp))
 fp=O/(kind+'.pending.fragment.json');fp.write_text(json.dumps({'kind':kind+'-source-bound-declaration-pending','classification_change':False,'functions':rows},indent=2)+'\n')
(E/'PROOF_SEAL01.json').write_text(json.dumps({'registry_guard':drift['registry_guard'],'new_pending_identities':48,'existing_pending_rebound':129,'ready_promotions':0,'fragments':[str((O/(kind+'.pending.fragment.json')).relative_to(L)) for kind in ['new','existing']],'readiness_admitted':False},indent=2)+'\n');c.unchanged();print('Sealed48 new pending identities and129 existing pending records; no registry write.')
