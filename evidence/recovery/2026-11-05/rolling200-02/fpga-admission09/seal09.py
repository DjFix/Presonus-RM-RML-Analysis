from pathlib import Path
import json,hashlib,sys,re,shutil
from elftools.elf.elffile import ELFFile
R=Path.cwd();L=R/'uc-library';E=R/'evidence/recovery/2026-11-05/rolling200-02/fpga-admission09';O=L/'validation/rolling200-fpga09'
sys.path.insert(0,str(L/'tools/registry'))
from adapter import snapshot
read=lambda p:json.loads(p.read_text())
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def ref(p):return {'path':str(p.relative_to(R)),'sha256':sha(p)}
auditpath=L/'candidates/rolling200_02_fpga_d0_audit/AUDIT.json';a=read(auditpath);oldproof=R/a['proof'];assert sha(oldproof)==a['proof_sha256']
historical=R/'temp/recovery-work/rolling200-02/agent-repos02/fpga_d0_audit';acceptpath=historical/'temp/recovery-work/root-fpga-audit01/PASSED.json';accepted=read(acceptpath);assert accepted['local_audit_passed'] and accepted['audit_sha256']==sha(auditpath)
for step in accepted['steps']:assert step['returncode']==0 and sha(historical/step['log'])==step['log_sha256']
for n,h in a['files'].items():assert sha(historical/n)==h,n
for n,h in a['files'].items():
 if not n.startswith('temp/'):assert sha(R/n)==h,n
integration=read(L/'validation/integration.json');assert integration['ctest_passed'] and integration['test_suites']==508 and integration==read(L/'validation/integration-linux.json')
for p,h in integration['files'].items():assert sha(L/p)==h,p
linux=R/'evidence/recovery/2026-11-05/rolling200-02/integration-linux08';assert read(linux/'COMPLETED.json')['passed']
assert re.search(r'Test\s+#\d+:\s+noaa_fpga_deleting_destructor_replay\s+\.{2,}\s+Passed',(linux/'tests.log').read_text())
role=json.loads((linux/'role-audit.log').read_text().splitlines()[-1]);assert role['passed']
installed=read(linux/'installed-audit.json');assert all(installed[k] for k in ['header_set_matches','compiled_mangles_matched','provider_sdk_matches'])
archives=read(L/'validation/rolling200-integrated08-r1/new.pending-proof.json')['archives'];name=a['original']['original_mangled']
for archive in ['presonus_uc','presonus_rm_components']:
 b=archives[archive];assert sha(R/b['path'])==b['sha256'] and sha(L/b['symbol_log'])==b['symbol_log_sha256'];assert name in {s.split()[-1] for s in (L/b['symbol_log']).read_text().splitlines() if s.split()}
orig=a['original'];elfpath=R/'rootfs/RML16AI_Rack_13731/home/root/mixer';assert sha(elfpath)==orig['elf_sha256']
with elfpath.open('rb') as stream:
 elf=ELFFile(stream);symbols=elf.get_section_by_name('.symtab').get_symbol_by_name(name);matches=[s for s in symbols if s['st_value']==orig['address'] and s['st_size']==orig['size']];assert len(matches)==1
 s=matches[0];sec=elf.get_section(s['st_shndx']);offset=sec['sh_offset']+s['st_value']-sec['sh_addr'];assert offset==orig['file_offset'];stream.seek(offset);assert hashlib.sha256(stream.read(s['st_size'])).hexdigest()==orig['range_sha256']
fmt=read(L/'validation/formatting.json');assert fmt['format_check_passed'];sources={n[len('uc-library/'):]:h for n,h in a['files'].items() if n.startswith('uc-library/')};providers={n:h for n,h in a['files'].items() if n.startswith('third_party/')}
for n,h in sources.items():
 assert sha(L/n)==h
 if Path(n).suffix in ['.cpp','.hpp','.h']:assert fmt['files'].get(n)==h,n
with snapshot(L) as current:
 assert not current.c.execute('SELECT status FROM records WHERE elf=? AND mangled=?',(orig['elf_sha256'],name)).fetchall();guard=current.guard
limitations=a['limitations'];domain=a['validation_domain']+' Current canonical 508-suite Linux replay, role/installed/compile-once and exact archive symbols passed. Existing canonical implementation audited; no new C++ reconstruction and no ready promotion. Native allocator and lazy singleton paths remain excluded.'
row=dict(original_elf_sha256=orig['elf_sha256'],mangled=name,demangled=orig['demangled'],firmware_version=orig['firmware_version'],role='server',original_address=orig['address'],original_size=orig['size'],address=orig['address'],size=orig['size'],section=orig['section_index'],sha256=orig['range_sha256'],portable_ready=False,cpp_compiled=True,mangling_namespace_checked=True,original_function_verified=False,hardware_verified=False,original_arm_abi_verified=False,original_declaration_verified=False,arm_differential_verified=False,domain=domain,validation_domain=domain,unresolved=limitations,sources=sources,repository_sources=providers,work_item_id=a['unique_work_item'])
promotion='Obtain independent original class/member/lifecycle declarations and establish equivalence for unobserved lazy singleton and allocation/exception paths before expanding scope; no ARM ABI/hardware inference from source-port execution.'
proof=dict(version=1,passed=True,cpp_compiled=True,compiled_mangled_names_matched=True,mangling_namespace_checked=True,portable_ready=False,active_source_replay_passed=True,source_guard_passed=True,bounded_cpp_replay_passed=True,hardware_verified=False,original_arm_abi_verified=False,original_declaration_verified=False,canonical_integration_sha256=sha(L/'validation/integration.json'),canonical_ctest_suites=508,formatting_sha256=sha(L/'validation/formatting.json'),formatter_version=fmt['formatter'],archives=archives,role_audit=role,full_linux_completion=ref(linux/'COMPLETED.json'),producer=ref(Path(__file__)),functions=[dict(row,native_range=orig,historical_audit=ref(auditpath),historical_behavior_proof=ref(oldproof),historical_local_acceptance=ref(acceptpath),historical_repository=str(historical),canonical_tests=['noaa_fpga_deleting_destructor_replay'],promotion_requirements=promotion)],new_reconstructed_elf_identities=0,new_audited_existing_identities=1,scope=domain)
O.mkdir(exist_ok=False);p=O/'pending-proof.json';p.write_text(json.dumps(proof,indent=2)+'\n');row.update(validation=str(p.relative_to(L)),validation_sha256=sha(p));(O/'pending.fragment.json').write_text(json.dumps({'kind':'existing-canonical-audit-declaration-pending','functions':[row]},indent=2)+'\n')
(E/'RECONSTRUCTION_REMARKS01.json').write_text(json.dumps({'original_elf_sha256':orig['elf_sha256'],'mangled':name,'work_item_id':a['unique_work_item'],'owner':'root','status':'pending-admission','domain':domain,'limitations':limitations,'history':a['history'],'retry_condition':promotion,'proof':ref(p)},indent=2)+'\n')
(E/'SEAL01.json').write_text(json.dumps({'registry_guard':guard,'new_reconstruction':False,'admitted':False,'new_pending_audit_identities':1,'proof':ref(p),'historical_proofs_unchanged':True},indent=2)+'\n')
print('Sealed existing FPGA D0 audit; registry unchanged')
