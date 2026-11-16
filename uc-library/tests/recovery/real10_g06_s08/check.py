"""Canonical supplied-object/executable lifecycle checker and worker compile entry."""
import argparse,datetime,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
C=Path('/home/rs/projects/opencs/ai-line-analysis')
PYTHON=C/'uc-library/.venv/bin/python';FMT=C/'uc-library/.venv/bin/clang-format'
SDK=C/'temp/core-upstream/root-integration-01/upstream-core/sdk/lib'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(argv,**kw):
 t=datetime.datetime.now(datetime.timezone.utc);r=subprocess.run(list(map(str,argv)),text=True,capture_output=True,check=True,**kw);return r.stdout,dict(argv=list(map(str,argv)),utc=t.isoformat(),seconds=(datetime.datetime.now(datetime.timezone.utc)-t).total_seconds(),stdout=r.stdout,stderr=r.stderr,returncode=r.returncode)

# Root canonical-only source/OBJECT/link provenance; local execution is retained.
def _canonical_observation(root, obj, exe, integration, source, providers=(), archives=()):
 if not integration or Path(integration).resolve() != (root/'uc-library/validation/integration.json').resolve():return None
 import importlib.util
 path=root/'uc-library/tools/recovery/canonical_compile_bindings.py'
 spec=importlib.util.spec_from_file_location('canonical_compile_bindings',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 result=module.bind(root,obj,source,exe_path=exe,required_provider_sources=providers,required_archive_names=archives)
 result['Root_canonical_transition']=module.load_transition(root,'temp/recovery-work/reconstruction10x10-20261116/workflow/checker-canonical-audit/review02/CANONICAL_BINDING_TRANSITION.json')
 result['Root_helper']={'path':'uc-library/tools/recovery/canonical_compile_bindings.py','sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
 return result

def _canonical_fields(binding):
 return {} if binding is None else {'canonical_compile_binding':binding,'canonical_binding_transition':binding['Root_canonical_transition'],'canonical_producer_helper':binding['Root_helper']}

def main(task=None):
 p=argparse.ArgumentParser();p.add_argument('--exe',required=True);p.add_argument('--object',required=True);p.add_argument('--integration',required=True);p.add_argument('--out',required=True);p.add_argument('--compile',action='store_true');p.add_argument('--task',default=task or Path(__file__).parent.name);a=p.parse_args();task=a.task;here=ROOT/'uc-library/tests/recovery'/task;exe=Path(a.exe).resolve();obj=Path(a.object).resolve();source=ROOT/'uc-library/src/Presonus/Mixer/ParamLink.cpp';header=ROOT/'uc-library/include/presonus/mixer/ParamLink.hpp';data=json.loads((here/'fixtures.json').read_text());commands=[]
 flags=['-std=c++17','-DCORE_USE_OPENSSL=1','-DNDEBUG=1','-DPRESONUS_HAS_UPSTREAM_CORE=1','-I'+str(ROOT/'uc-library/include'),'-isystem',str(ROOT/'third_party/ccl-framework'),'-O3','-Wall','-Wextra','-Wpedantic','-pthread','-Ulinux']
 if a.compile:
  exe.parent.mkdir(parents=True,exist_ok=True);obj.parent.mkdir(parents=True,exist_ok=True)
  for argv in [['/usr/bin/c++',*flags,'-MD','-MF',str(obj)+'.d','-c',source,'-o',obj],['/usr/bin/c++',*flags,'-fno-rtti','-MD','-MF',str(exe)+'.d',here/'Replay.cpp',ROOT/'uc-library/src/Presonus/Mixer/ControlMapping.cpp',obj,SDK/'libcorelib.a',SDK/'libpresonus_core_allocator.a','-ldl','-o',exe]]:
   _,log=run(argv);commands.append(log)
  Path(str(exe)+'.compile.json').write_text(json.dumps(commands,indent=2)+'\n');return
 binding=_canonical_observation(ROOT,obj,exe,a.integration,str(source.relative_to(ROOT)),providers=('uc-library/src/Presonus/Mixer/ControlMapping.cpp',))
 names,log=run(['/usr/bin/nm','--defined-only',obj]);commands.append(log);assert data['mangled'] in {l.split()[-1] for l in names.splitlines() if l.split()}
 stdin=''.join(f"{int(c['present'])} {int(c['flag'])} {int(bool(c['name']))}\n" for c in data['cases']);output,log=run([exe,data['variant'][1]],input=stdin);commands.append(log)
 lines=[list(map(int,l.split())) for l in output.splitlines()];assert len(lines)==len(data['cases'])
 for line,c in zip(lines,data['cases']):
  assert line==[1,c['flag_written'],int(c['target']==0),int(c['present']),min(len(c['name']),31),0],(line,c)
 _,log=run([FMT,'--style=file','--fallback-style=LLVM','--dry-run','--Werror',header,source,ROOT/'uc-library/tests/recovery/real10_g06_s08/Replay.cpp',here/'Replay.cpp']);commands.append(log)
 paths={header,source,here/'Replay.cpp',here/'native.py',here/'check.py',here/'fixtures.json',ROOT/'uc-library/tests/recovery/real10_g06_s08/Replay.cpp',ROOT/'uc-library/tests/recovery/real10_g06_s08/native.py',ROOT/'uc-library/tests/recovery/real10_g06_s08/check.py',ROOT/'uc-library/src/Presonus/Mixer/ControlMapping.cpp',ROOT/'third_party/ccl-framework/core/portable/corecomponent.cpp',ROOT/'third_party/ccl-framework/core/portable/coreparams.cpp'}
 for dep in ([] if binding is not None else [Path(str(obj)+'.d'),Path(str(exe)+'.d')]):
  if dep.exists():
   for token in dep.read_text().replace('\\\n',' ').split()[1:]:
    q=Path(token);q=q if q.is_absolute() else ROOT/q
    if q.is_file() and q.is_relative_to(ROOT):paths.add(q)
 if binding is not None:paths.update(ROOT/p for p in binding['files'])
 binds={str(q.relative_to(ROOT)):sha(q) for q in sorted(paths)}
 domain='8 exact constructor cases: null/non-null borrowed parameter, false/true bool, empty and long copied name. Native flag/target initialization and addObserver branch compared with real canonical ControlMapping and pinned CCL observer count; separately invoke exact host C1/C2 symbols; actual cleanup removes observer without deleting borrowed parameter.'
 limits=['Original class layout/inheritance/ARM ABI unresolved; actual canonical ControlMapping plus pinned CCL ParamObserverBase used as explicit source adaptation.','Original distinct C1/C2 byte ranges checked separately; host C1/C2 aliases invoked separately.','Native ControlMapping/addObserver bodies are boundary stubs; actual host provider registration/base construction observed independently.','Observer callback helper implemented from supplemental original instructions; constructor replay covers unbound-target notification only. Numeric/string forwarding needs separate helper coverage and receives no constructor readiness credit.','Destructor is independent source-port cleanup, not recovery of an original ParamLink destructor. No allocation-failure/EH/concurrency/hardware claim.']
 row=dict(original_elf_sha256=data['original_elf_sha256'],mangled=data['mangled'],sources={str(q.relative_to(ROOT/'uc-library')):sha(q) for q in paths if q.is_relative_to(ROOT/'uc-library')},repository_sources={str(q.relative_to(ROOT)):sha(q) for q in paths if q.is_relative_to(ROOT/'third_party')},domain=domain,portable_ready=False,cpp_compiled=True,mangling_namespace_checked=True,declaration_uncertainties=['Original class declaration/inheritance/layout unresolved; portable explicit ownership/base model.'])
 proof=dict(version=1,task_id=task,session_id='01a1e2e7-862b-78c3-9f29-e8aad84be223',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),functions=[dict(row,original_range=data['original_range'],case_count=len(lines),cpp_differential_passed=True)],proposed_readiness=dict(ready=[],pending=[row]),cpp_compiled=True,cpp_differential_passed=True,compiled_mangled_names_matched=True,source_bindings=binds,commands=commands,original_arm_abi_verified=False,hardware_verified=False,limitations=limits,formatter=run([FMT,'--version'])[0].strip(),compiled_object=dict(path=str(obj),sha256=sha(obj)),executable=dict(path=str(exe),sha256=sha(exe)),canonical_integration_completed=False)
 proof.update(_canonical_fields(binding))
 if a.integration!='none':proof['fresh_integration_reference']=dict(path=str(Path(a.integration).resolve()),sha256=sha(a.integration))
 out=Path(a.out).resolve();out.parent.mkdir(parents=True,exist_ok=True)
 if out.is_relative_to(ROOT/'uc-library/candidates'):
  raise ValueError('Replay output must be scratch/current proof, not hash-bound candidate artifact')
 if out.exists():
  previous=out.read_bytes();history=out.with_name(out.stem+'.previous-'+hashlib.sha256(previous).hexdigest()+out.suffix)
  if history.exists():assert history.read_bytes()==previous,'Scratch history hash collision'
  else:
   with history.open('xb') as stream:stream.write(previous)
 out.write_text(json.dumps(proof,indent=2)+'\n');print(task,'PASS8')
if __name__=='__main__':main()
