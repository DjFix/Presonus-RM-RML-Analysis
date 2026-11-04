"""Fresh compatibility proof for a source relocation; no reconstruction credit."""
from pathlib import Path
import copy, hashlib, json, subprocess, sys, datetime
from elftools.elf.elffile import ELFFile
R=Path.cwd();L=R/'uc-library';E=R/'evidence/recovery/2026-11-05/canonical-organization04';B=R/'temp/core-upstream/root-integration-01';O=L/'validation/canonical-organization-panelpresets04'
sys.path[:0]=[str(L/'tools'),str(L/'tools/registry')]
from merge_readiness import ValidationCache,repository_sources_match
from adapter import snapshot
c=ValidationCache();sha=c.sha
completion=c.read_json(E/'linux02/COMPLETED.json');assert completion['passed'] and completion['test_suites']==453
integration=c.read_json(L/'validation/integration.json');assert integration==c.read_json(L/'validation/integration-linux.json');assert integration['ctest_passed'] and integration['test_suites']==453
for name,h in integration['files'].items():assert sha(L/name)==h,name
fmt=c.read_json(L/'validation/formatting.json');assert fmt['format_check_passed']
affected=c.read_json(E/'AFFECTED.json');assert not affected['unexpected_missing'];assert len(affected['affected'])>0 and all(x['status']=='pending' and not x['repository_changes'] for x in affected['affected'])
with snapshot(L) as s:assert s.guard==affected['registry_guard'],'Registry changed after drift scan'
O.mkdir(exist_ok=False)
testlog=E/'linux02/tests.log';testtext=testlog.read_text()
required_tests=['frontier01_w01_native','frontier01_w01_replay','reconstruction200_large02_w06']
import re
for name in required_tests:
 assert re.search(r'Test #\d+: '+re.escape(name)+r'\s+\.+\s+Passed',testtext),name
body=c.read_json(E/'BODY_EQUIVALENCE.json');assert all(v['moved_body_preserved'] and sha(L/p)==v['sha256'] for p,v in body['files'].items())
archives={};names={}
for target in ['presonus_uc','presonus_cs18_components','presonus_rm_components']:
 p=B/('lib'+target+'.a');log=O/(target+'-nm.log');result=subprocess.check_output(['nm','--defined-only',str(p)],text=True);log.write_text(result);names[target]={x.split()[-1] for x in result.splitlines() if x.split()};archives[target]={'path':str(p.relative_to(R)),'sha256':sha(p),'symbol_log':str(log.relative_to(L))}
role=json.loads((E/'linux02/role-audit.log').read_text().splitlines()[-1]);assert role['passed'];installed=c.read_json(E/'linux02/installed-audit.json');assert all(installed[k] for k in ['header_set_matches','compiled_mangles_matched','provider_sdk_matches'])
elfs={'304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0':R/'rootfs/CS18_v13840/home/root/surface','9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07':R/'rootfs/RML16AI_Rack_13731/home/root/mixer'};ranges={}
for digest,path in elfs.items():
 assert sha(path)==digest
 wanted={x['entry']['mangled']:x['entry'] for x in affected['affected'] if x['entry']['original_elf_sha256']==digest}
 with path.open('rb') as stream:
  elf=ELFFile(stream);syms={s.name:s for section in elf.iter_sections() if section['sh_type']=='SHT_SYMTAB' for s in section.iter_symbols() if s.name in wanted}
  assert set(syms)==set(wanted)
  for name,row in wanted.items():
   sym=syms[name];address=sym['st_value'];size=sym['st_size'];sec=elf.get_section(sym['st_shndx']);assert sec['sh_type']!='SHT_NOBITS';offset=sec['sh_offset']+address-sec['sh_addr'];stream.seek(offset);h=hashlib.sha256(stream.read(size)).hexdigest()
   assert address==row.get('original_address',row.get('address',address)) and size==row.get('original_size',row.get('size',size))
   if row.get('sha256'):assert h==row['sha256']
   ranges[(digest,name)]={'elf_sha256':digest,'mangled':name,'address':address,'size':size,'section':sec.name,'section_index':sym['st_shndx'],'file_offset':offset,'bytes_sha256':h}
assert subprocess.check_output(['git','-C',str(R/'third_party/ccl-framework'),'rev-list','--parents','-n','1','HEAD'],text=True).strip()=='e8cbdea4a4a20e15111f5a690798a259c0374b31'
rows=[];functions=[]
for item in affected['affected']:
 row=copy.deepcopy(item['entry']);previous={'path':row['validation'],'sha256':row['validation_sha256']};assert sha(L/previous['path'])==previous['sha256'];changed={x['old_path']:x for x in item['changes']};sources={}
 for old,h in row['sources'].items():
  outputs=affected['mapping'].get(old,[old])
  for new in outputs:
   now=sha(L/new)
   if outputs!=[old] or h!=now:assert old in changed and changed[old]['outputs'][new]==now
   sources[new]=now
   if Path(new).suffix in ['.cpp','.hpp','.h']:assert fmt['files'].get(new)==now,new
 assert repository_sources_match(L,row,c)
 provider='third_party/ccl-framework/core/portable/corestorage.h'
 row.setdefault('repository_sources',{})[provider]=sha(R/provider)
 role_target='presonus_cs18_components' if row['original_elf_sha256'].startswith('304c') else 'presonus_rm_components';assert row['mangled'] in names[role_target] and row['mangled'] in names['presonus_uc']
 domain=row.get('domain',row.get('validation_domain',''))+' Fresh compatibility after canonical channel/GEQ/scene preset split and FX consolidation: implementation bodies preserved modulo formatter whitespace, direct dependencies clarified and existing replay call boundary preserved; all453 Linux suites, existing bounded native/provider/host replays and role/install/compile-once gates repeated. Every prior declaration-pending uncertainty, native assumption and exclusion remains. No new reconstruction, declaration, ABI or hardware credit.'
 row.update(sources=sources,previous_validation=previous,validation=str((O/'pending.compat-proof.json').relative_to(L)),domain=domain,validation_domain=domain,portable_ready=False,cpp_compiled=True,mangling_namespace_checked=True)
 promotion={'status':'declaration-pending','required_evidence':'Independent evidence establishing unresolved original ordinary return/signature declarations and any method-specific uncertainties retained in the prior record/proof; source relocation and matching mangling do not establish these.','prior_unresolved':row.get('unresolved',row.get('declaration_uncertainties'))}
 functions.append({'original_elf_sha256':row['original_elf_sha256'],'mangled':row['mangled'],'validation_domain':domain,'previous_validation':previous,'changes':item['changes'],'sources':sources,'repository_sources':row.get('repository_sources',{}),'native_range':ranges[(row['original_elf_sha256'],row['mangled'])],'promotion_requirements':promotion});rows.append(row)
proof={'version':1,'passed':True,'cpp_compiled':True,'compiled_mangled_names_matched':True,'mangling_namespace_checked':True,'cpp_differential_passed':True,'portable_ready':False,'active_source_replay_passed':True,'source_guard_passed':True,'arm_differential_passed':True,'new_native_execution_claimed':True,'native_behavior_credit_added':False,'new_reconstructed_functions':0,'hardware_verified':False,'original_arm_abi_verified':False,'original_declaration_verified':False,'scope':'Organization-only compatibility; original ARM oracle repeated within its unchanged bounded domain. No old proof relabeled. All prior limitations retained.','canonical_integration_sha256':sha(L/'validation/integration.json'),'canonical_ctest_suites':453,'formatting_sha256':sha(L/'validation/formatting.json'),'formatter_version':fmt['formatter'],'archives':archives,'role_audit':role,'functions':functions,'move_manifest':{'path':str((E/'MOVES.json').relative_to(R)),'sha256':sha(E/'MOVES.json')},'native_replay':{'scope':'Existing bounded original-instruction oracle and provider/host tests repeated by full CTest; no broadened native coverage or all-identities differential claim','required_tests':required_tests,'test_log':str(testlog.relative_to(R)),'test_log_sha256':sha(testlog),'body_equivalence':{'path':str((E/'BODY_EQUIVALENCE.json').relative_to(R)),'sha256':sha(E/'BODY_EQUIVALENCE.json')}},'producer':{'path':str(Path(__file__).relative_to(R)),'sha256':sha(Path(__file__))}}
p=O/'pending.compat-proof.json';p.write_text(json.dumps(proof,indent=2)+'\n')
for row in rows:row['validation_sha256']=sha(p)
(O/'pending.compat.fragment.json').write_text(json.dumps({'kind':'existing-record-canonical-source-relocation','classification_change':False,'new_reconstructed_functions':0,'functions':rows},indent=2)+'\n');c.unchanged();print(str(len(rows))+' pending identities freshly rebound; no admission or classification change yet')
