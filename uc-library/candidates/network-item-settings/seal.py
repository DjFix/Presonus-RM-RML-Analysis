#!/usr/bin/env python3
"""Run local checks and seal per-packet handoffs; never changes global ledgers."""
import collections,datetime,hashlib,json,subprocess,time
from pathlib import Path
B=Path('uc-library/candidates/network-item-settings')
E=Path('evidence/recovery/2026-11-05/network-item-settings')
P=Path('temp/recovery-work/rolling200-02/implementation-plan01/packets-current-network-items02/packets')
PYTHON='uc-library/.venv/bin/python'
SOURCES=['uc-library/include/presonus/uc/NetworkItem.hpp','uc-library/include/presonus/surface/NetworkSetupComponent.hpp','uc-library/src/Presonus/Surface/NetworkSetupComponent.cpp']
TEST='uc-library/tests/recovery/NetworkItemSettingsReplay.cpp'
FORMAT=['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror']+SOURCES+[TEST]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def check(kind,argv):return dict(kind=kind,argv=argv,timeout_seconds=120)
checks=[check('format',FORMAT),check('compile',[PYTHON,str(B/'build.py')]),check('symbols',[PYTHON,str(B/'symbols.py')]),check('oracle',[PYTHON,str(B/'native_oracle.py'),'--executable','temp/recovery-work/network-item-settings/replay','--verify']),check('replay',[PYTHON,str(B/'replay.py'),'--executable','temp/recovery-work/network-item-settings/replay','--fixtures',str(B/'fixtures.json')])]
E.mkdir(parents=True,exist_ok=True)
logs=[]
for i,c in enumerate(checks):
 started=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic();r=subprocess.run(c['argv'],text=True,capture_output=True,timeout=c['timeout_seconds']);path=E/f'{i:02d}-{c["kind"]}.log';path.write_text(r.stdout+r.stderr);logs.append(dict(**c,start_utc=started,seconds=time.monotonic()-t,returncode=r.returncode,log=str(path),log_sha256=sha(path)));assert r.returncode==0,(c,r.stdout,r.stderr)
f=json.loads((B/'fixtures.json').read_text())
versions={k:subprocess.check_output(v,text=True).strip() for k,v in {'formatter':['uc-library/.venv/bin/clang-format','--version'],'compiler':['c++','--version'],'symbol_tool':['nm','--version'],'ccl_root':['git','-C','third_party/ccl-framework','log','--max-parents=0','--format=%H %s']}.items()}
deps=['third_party/ccl-framework/core/portable/corepersistence.h','third_party/ccl-framework/core/portable/corepersistence.cpp','third_party/ccl-framework/core/portable/coreattributes.h','third_party/ccl-framework/core/portable/coreattributes.cpp','third_party/ccl-framework/core/public/corestringbuffer.h','third_party/ccl-framework/core/public/corestringtraits.h','uc-library/src/Presonus/UC/NetworkItem.cpp','uc-library/include/presonus/delay_timer.hpp','uc-library/include/presonus/surface/MidiMixerHandler.hpp','rootfs/CS18_v13840/home/root/surface']
libs=['libpresonus_cs18_components.a','libpresonus_uc.a','upstream-core/sdk/lib/libcorelib.a','upstream-core/sdk/lib/libpresonus_core_allocator.a','private-glibc29-provider/libpresonus_private_glibc29.a']
deps += ['temp/core-upstream/root-integration-01/'+x for x in libs]
artifacts=[]
def artifact(kind,p):
 p=str(p)
 if not any(x['path']==p for x in artifacts):artifacts.append(dict(kind=kind,path=p,sha256=sha(p)))
for p in SOURCES:artifact('source',p)
artifact('test',TEST)
for p in sorted(B.glob('*.py')):artifact('replay' if p.name=='replay.py' else 'producer',p)
artifact('fixture',B/'fixtures.json')
for p in deps:artifact('dependency',p)
for i in (1,2):
 packet=P/f'rolling200_02_network_items_{i:02d}'
 for name in ('context.json','request.json','TASK.md','ELF_CONTEXT.md','SOURCE_SLICES.md','CONTEXT.md'):artifact('packet',packet/name)
for item in logs:artifact('log',item['log'])
limitations=f['limitations']+' Provisional void storeSelected/bool isStoredItem returns stay declaration-pending. Independent portable identity accessor/storage does not recover native fields. Direct provider protocol normalizes null getString to empty text, equivalent for observed CStringBuffer64 construction. Public CCL adapter defers private lookupOrAdd allocation until following make/set; allocation failure and interleaving are outside scope. Production partition and canonical full Linux/readiness checks remain Root work.'
proof=dict(version=1,date=datetime.datetime.now(datetime.timezone.utc).isoformat(),session_id='/root/rolling200_02_network_items',repository=str(Path.cwd()),baseline='d548724a88fbb82e34f7a43b1c56081c6afda7c9',ranges=f['ranges'],versions=versions,checks=logs,source_and_dependency_bindings=artifacts.copy(),native_cases=len(f['cases']),per_method=dict(collections.Counter(str(r['input']['method']) for r in f['cases'])),original_execution='Exact original ARM caller instructions in Unicorn2.1.4, verified ELF section ranges. Guarded PC and target writes; initialized singleton. No original Core execution.',portable_execution='Compiled canonical original-scope methods with actual pinned CCL5.0.0 SettingFile/Attributes/CStringBuffer64; separate provider branch supplies direct CCL observations to native calls. No reconstructed method executes in provider branch.',objects={p:sha(p) for p in ['temp/recovery-work/network-item-settings/NetworkSetupComponent.o','temp/recovery-work/network-item-settings/replay']},limitations=limitations,local_checks_passed=True,readiness_admitted=False)
proofpath=E/'proof.json';proofpath.write_text(json.dumps(proof,indent=2)+'\n');artifact('proof',proofpath)
remarks=[]
for i in (1,2):
 packet=P/f'rolling200_02_network_items_{i:02d}';request=json.loads((packet/'request.json').read_text());o=request['originals'][0]['original']
 original={k:o[v] for k,v in {'elf_sha256':'elf','firmware':'firmware','role':'role','mangled':'mangled','address':'address','size':'size'}.items()};original['section']='.text'
 domain='304 native/provider cases: flags bit2 including signed values; null item clearing; missing/present section; initial dirty false/true; terminated identities every length0..63; unrelated setting preservation; key boundaries.' if i==1 else '222 native/provider cases: empty/missing saved values and sections; empty saved null item short circuit; matching/mismatch/case-sensitive identities every length0..63; saved63..127 truncation; section creation without dirty flag; unrelated preservation.'
 delivery=B/f'rolling200_02_network_items_{i:02d}';delivery.mkdir(exist_ok=True)
 handoff=dict(version=1,task_id=request['task_id'],namespace=request['namespace'],packet_manifest=str(packet/'context.json'),originals=[original],artifacts=artifacts,checks=checks,validation_domain=domain,limitations=limitations,build_integration=dict(partition='Existing NetworkSetupComponent.cpp OBJECT partition retained; no new production CPP.',public_headers=SOURCES[:2],test_target='NetworkItemSettingsReplay',test_source=TEST,link_dependencies=['current NetworkSetupComponent object','current NetworkItem.cpp','actual CCL corelib and existing CS18/UC archives','pinned allocator/private glibc29 provider','pthread','dl','z'],ctest_argv=[PYTHON,str(B/'replay.py'),'--executable','<canonical built NetworkItemSettingsReplay>','--fixtures',str(B/'fixtures.json'),'--method',str(i)],fixture_sha256=sha(B/'fixtures.json'),source_port_dependencies=deps))
 (delivery/'HANDOFF.json').write_text(json.dumps(handoff,indent=2)+'\n')
 remarks.append(dict(date='2026-11-05',original=original,work_item=request['work_binding']['work_item_id'],status='compiled-declaration-pending-local-checks-pass',observation=limitations,validation_domain=domain,evidence=str(proofpath),resolution_or_retry_condition='New independent original declaration/layout evidence can refine pending return types; hardware only with explicit authorization. Root must integrate and apply full canonical/readiness gates.'))
(E/'REMARKS.json').write_text(json.dumps(remarks,indent=2)+'\n')
for i in (1,2):
 path=B/f'rolling200_02_network_items_{i:02d}'/'HANDOFF.json'
 handoff=json.loads(path.read_text())
 handoff['artifacts'].append(dict(kind='remarks',path=str(E/'REMARKS.json'),sha256=sha(E/'REMARKS.json')))
 path.write_text(json.dumps(handoff,indent=2)+'\n')
print(json.dumps({'passed':True,'handoffs':[str(B/f'rolling200_02_network_items_{i:02d}'/'HANDOFF.json') for i in (1,2)],'native_cases':len(f['cases'])}))
