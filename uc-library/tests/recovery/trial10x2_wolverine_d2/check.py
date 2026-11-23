#!/usr/bin/env python3
import argparse,datetime,hashlib,json,os,subprocess,time
from pathlib import Path
import native
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent;TASK=T.name
P=R/'temp/recovery-work/trial10x2-20261115/prepared01/packets'/TASK
REQ=json.loads((P/'request.json').read_text());TARGET=REQ['targets'][0]
WORK=R/'temp/recovery-work'/TASK
SOURCE=['uc-library/include/presonus/panel/WolverinePanelComponent.hpp','uc-library/src/Presonus/Panel/WolverinePanelComponent.cpp']
OWN=SOURCE+[str(T.relative_to(R)/'Replay.cpp')]
SNAP=Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/trial10x2-20261115/prepared01/snapshot')
DOMAIN='10 independent exact original ARM invocations per variant at two receiver addresses; nonempty 1/2/5/16/64 actual CCL parameter and owned-child resources, three real CCL borrowed-control pointer vectors, actual borrowed PanelTask scheduling; observed owned child destruction, parameter deallocation, preserved task/dependency and genuine unsized object free. Provider boundary sequence derived from native calls, fulfilled through actual canonical Rack/CCL destruction and unsized host delete; portable product compared independently.'
LIMITS=['Independent tagged constructor and actual canonical Rack source-port base only. Original constructor/member layout/inheritance/EH, ARM ABI, vtable byte identity and hardware remain unresolved.','Native execution stops at actual base/global-delete boundaries; actual host providers fulfill those operations. No native Rack/Core body behavior equivalence or original field ownership is claimed.','Nonempty stable resources only; borrowed task/dependencies outlive destruction. No cleanup() invention: Rack destructor is actually defaulted, distinct from explicit cleanup(). No class-specific operator delete.','D1 host alias is recorded as a compiler output only; original targeted D2/D0 ranges remain separate and only assigned identity receives proposed credit.']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(argv,input=None):
 argv=list(map(str,argv));start=time.monotonic();r=subprocess.run(argv,cwd=R,input=input,text=True,capture_output=True,env={**os.environ,'TMPDIR':str(WORK)})
 with (WORK/'commands.jsonl').open('a') as f:f.write(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),seconds=time.monotonic()-start,argv=argv,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))+'\n')
 if r.returncode:print(r.stdout,r.stderr);r.check_returncode()
 return r.stdout

SUPPLEMENT=Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/trial10x2-20261115/root-review/provider-supplement/PROVIDERS.json')
APPROVAL=SUPPLEMENT.with_name('ROOT_APPROVAL.json')
def providers():
 assert sha(SUPPLEMENT)=='0e4fc25d3383ae8609932b7e25c4d28bac3ee92b9435c11e8d63b61cd29f0c18'
 data=json.loads(SUPPLEMENT.read_text())
 for item in list(data['archives'].values()):assert sha(item['frozen_read_path'])==item['sha256']
 for item in data['system_libraries']:assert sha(item['path'])==item['sha256']
 return [Path(data['archives'][name]['frozen_read_path']) for name in ['libpresonus_rm_components.a','libcorelib.a','libpresonus_core_allocator.a','libpresonus_private_glibc29.a']]
def fmt():
 v=run(['uc-library/.venv/bin/clang-format','--version']).strip();run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*OWN]);return v

def compile():
 flags=['/usr/bin/c++','-std=c++17','-O2','-fno-rtti','-fno-lto','-fno-sized-deallocation','-Wno-multichar','-ffunction-sections','-fdata-sections','-Ulinux','-pthread','-Iuc-library/include','-Ithird_party/ccl-framework']
 run(flags+['-MMD','-MF',WORK/'production.d','-c',SOURCE[1],'-o',WORK/'production.o']);run(flags+['-MMD','-MF',WORK/'driver.d','-c',OWN[2],'-o',WORK/'driver.o'])
 run(['/usr/bin/c++',WORK/'production.o',WORK/'driver.o','-Wl,--gc-sections','-Wl,--start-group',*providers(),'-Wl,--end-group','-pthread','-ldl','-lm','-lz','/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lssl','-lcrypto','/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so','-o',WORK/'replay'])

def symbols(obj):
 s=run(['nm','--defined-only',obj]);names=[x.split()[-1] for x in s.splitlines() if x.split()]
 for suffix in ['D0Ev','D1Ev','D2Ev']:assert '_ZN8Presonus5Panel23WolverinePanelComponent'+suffix in names
 dis=run(['objdump','-dr',obj]);start=dis.index('<_ZN8Presonus5Panel23WolverinePanelComponentD0Ev>:');part=dis[start:].split('\n\n')[0];assert '_ZdlPv' in part and '_ZdlPvm' not in part
 return s,part

def replay(exe):
 f=json.loads((T/'fixtures.json').read_text());payload=''.join(' '.join(map(str,c['input']))+'\n' for c in f['cases']);out=run([exe],input=payload).splitlines();assert len(out)==len(f['cases'])
 for c,o in zip(f['cases'],out):assert o==c['provider_observation'],(c,o)
 return len(out)
def native_check(exe):
 f=native.generate(exe.resolve());assert f==json.loads((T/'fixtures.json').read_text());return f

def current_source_transition(a):
 if not (a.current_source_transition or a.current_source_transition_sha256):return {}
 assert a.current_source_transition and a.current_source_transition_sha256
 assert sha(a.current_source_transition)==a.current_source_transition_sha256
 transition=json.loads(a.current_source_transition.read_text())
 assert transition['version']==1 and TASK in transition['tests']
 changes=transition['current_sources']
 assert {CONTROL_GROUP_HEADER} <= set(changes) <= {CONTROL_GROUP_HEADER, PANEL_COMPONENT_HEADER, RACK_PANEL_HEADER, RACK_PANEL_SOURCE}
 return changes

CONTROL_GROUP_HEADER='uc-library/include/presonus/surface_panel/ControlGroup.hpp'
PANEL_COMPONENT_HEADER='uc-library/include/presonus/panel/PanelComponent.hpp'
RACK_PANEL_HEADER='uc-library/include/presonus/panel/RackPanelComponent.hpp'
RACK_PANEL_SOURCE='uc-library/src/Presonus/Panel/RackPanelComponent.cpp'
def source_closure(changes):
 snapshot=json.loads((SNAP.parent/'SNAPSHOT.json').read_text());supp=json.loads(SUPPLEMENT.read_text());observed={}
 def current_hash(path,expected):
  if path not in changes:return expected
  change=changes[path]
  assert expected and expected==change['previous_sha256']
  assert sha(change['previous_frozen_read_path'])==expected
  result=change['current_sha256']
  assert sha(change['current_frozen_read_path'])==result
  return result
 for source in [SOURCE[1],OWN[2]]:
  text=run(['/usr/bin/c++','-std=c++17','-fno-sized-deallocation','-fno-rtti','-Wno-multichar','-Ulinux','-pthread','-Iuc-library/include','-Ithird_party/ccl-framework','-MM','-MT','closure',source]).replace('\\\n',' ')
  for path in text.split(': ',1)[1].split():
   if path in OWN:continue
   expected=snapshot['files'].get(path) or supp['read_inputs'].get(path,{}).get('sha256')
   expected=current_hash(path,expected)
   assert expected and sha(R/path)==expected,('unsealed compiler input',path)
   observed[path]=expected
 for path in ['uc-library/src/Presonus/Panel/RackPanelComponent.cpp','uc-library/src/Presonus/Panel/PanelComponentLifecycle.cpp','uc-library/src/Presonus/Panel/control.cpp']:
  expected=snapshot['files'].get(path) or supp['read_inputs'].get(path,{}).get('sha256')
  expected=current_hash(path,expected)
  assert expected and sha(R/path)==expected,path
  observed[path]=expected
 assert set(changes)<=set(observed)
 return observed

def proof(a):
 version=fmt();sym,dis=symbols(a.object);exe_sym,exe_dis=symbols(a.exe);f=native_check(a.exe);count=replay(a.exe)
 sources={p.removeprefix('uc-library/'):sha(R/p) for p in SOURCE+['uc-library/include/presonus/panel/RackPanelComponent.hpp','uc-library/src/Presonus/Panel/RackPanelComponent.cpp','uc-library/include/presonus/panel/PanelComponent.hpp','uc-library/src/Presonus/Panel/PanelComponentLifecycle.cpp']}
 deps={p:sha(R/p) for p in ['third_party/ccl-framework/core/portable/corecomponent.h','third_party/ccl-framework/core/portable/corecomponent.cpp','third_party/ccl-framework/core/portable/coreparams.h','third_party/ccl-framework/core/portable/coreparams.cpp','third_party/ccl-framework/core/public/corevector.h']}
 record=dict(original_elf_sha256=TARGET['original_elf_sha256'],mangled=TARGET['mangled'],demangled='Presonus::Panel::WolverinePanelComponent::~WolverinePanelComponent()',firmware=TARGET['firmware'],role=TARGET['role'],address=TARGET['address'],size=TARGET['size'],section=TARGET['section'],portable_ready=False,cpp_compiled=True,mangling_namespace_checked=True,validation_domain=DOMAIN,sources=sources,repository_sources=deps,declaration_uncertainties=LIMITS,original_function_verified=False,hardware_verified=False)
 result=dict(task_id=TASK,timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),native=f,sources=sources,repository_sources=deps,cpp_differential_passed=True,compiled_original_mangled_names_matched=True,compiled_symbols=sym,deleting_destructor_disassembly=dis,portable_case_count=count,formatting=dict(version=version,passed=True,sources=sources),validation_domain=DOMAIN,limitations=LIMITS,canonical_binding_pending=not bool(a.integration),proposed_readiness=dict(ready=[],pending=[record]),binary_bindings={str(a.exe):sha(a.exe),str(a.object):sha(a.object)},provider_libraries={str(p):sha(p) for p in providers()},fixture_sha256=sha(T/'fixtures.json'),producer_sha256=sha(__file__),test_sources={OWN[2]:sha(R/OWN[2])})
 result['compiler_provider_source_closure']=source_closure(current_source_transition(a))
 if a.current_source_transition:result['current_source_transition']={'path':str(a.current_source_transition),'sha256':a.current_source_transition_sha256}
 result['current_dependency_query']='Fresh compiler -MM over current owned production and replay source, no worker depfile/cache input'
 result['supplied_executable_deleting_destructor_disassembly']=exe_dis
 result['historical_worker_compile_provenance']='Preserved separately under evidence/recovery/2026-11-15/trial10x2-wolverine/repair01; not represented as current canonical compilation' 
 result['provider_supplement']={'path':str(SUPPLEMENT),'sha256':sha(SUPPLEMENT),'approval':str(APPROVAL),'approval_sha256':sha(APPROVAL)}
 if a.integration:result['integration']={'path':str(a.integration),'sha256':sha(a.integration)}
 out=a.out or R/'uc-library/candidates'/TASK/'worker-proof.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n');print(out)
def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['format','compile','symbols','native','replay','proof']);p.add_argument('--exe',type=Path,default=WORK/'replay');p.add_argument('--object',type=Path,default=WORK/'production.o');p.add_argument('--integration',type=Path);p.add_argument('--out',type=Path);p.add_argument('--current-source-transition',type=Path);p.add_argument('--current-source-transition-sha256');a=p.parse_args();WORK.mkdir(parents=True,exist_ok=True)
 if a.mode=='format':print(fmt())
 elif a.mode=='compile':compile()
 elif a.mode=='symbols':print(symbols(a.object))
 elif a.mode=='native':print(len(native_check(a.exe)['cases']))
 elif a.mode=='replay':print(replay(a.exe))
 else:proof(a)
if __name__=='__main__':main()
