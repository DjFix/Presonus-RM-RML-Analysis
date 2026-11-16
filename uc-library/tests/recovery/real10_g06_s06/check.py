"""Supplied binary differential checker; no implicit compilation in replay mode."""
import argparse, datetime, hashlib, json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
TASK=HERE.name
SOURCE=ROOT/'uc-library/src/Presonus/Mixer/FXComponent.cpp'
HEADER=ROOT/'uc-library/include/presonus/mixer/FXComponent.hpp'
BUILD=ROOT/'temp/recovery-work/real10_g06'
CANONICAL=Path('/home/rs/projects/opencs/ai-line-analysis')
FMT=CANONICAL/'uc-library/.venv/bin/clang-format'
PYTHON=CANONICAL/'uc-library/.venv/bin/python'
SDK=CANONICAL/'temp/core-upstream/root-integration-01/upstream-core/sdk/lib'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(args,**kw):
 r=subprocess.run(list(map(str,args)),text=True,capture_output=True,check=True,**kw);return r.stdout

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

def main():
 p=argparse.ArgumentParser();p.add_argument('--exe',required=True);p.add_argument('--object',required=True);p.add_argument('--integration',required=True);p.add_argument('--out',required=True);p.add_argument('--compile',action='store_true');a=p.parse_args();exe=Path(a.exe).resolve();obj=Path(a.object).resolve()
 flags=['-std=c++17','-DCORE_USE_OPENSSL=1','-DNDEBUG=1','-DPRESONUS_HAS_UPSTREAM_CORE=1','-I'+str(ROOT/'uc-library/include'),'-isystem',str(ROOT/'third_party/ccl-framework'),'-O3','-Wall','-Wextra','-Wpedantic','-pthread','-Ulinux']
 commands=[]
 if a.compile:
  exe.parent.mkdir(parents=True,exist_ok=True);obj.parent.mkdir(parents=True,exist_ok=True)
  for cmd in [['/usr/bin/c++',*flags,'-MD','-MF',str(obj)+'.d','-c',SOURCE,'-o',obj],['/usr/bin/c++',*flags,'-MD','-MF',str(exe)+'.d',HERE/'Replay.cpp',ROOT/'uc-library/src/Presonus/DspComponent.cpp',obj,SDK/'libcorelib.a',SDK/'libpresonus_core_allocator.a','-ldl','-o',exe]]:
   run(cmd);commands.append(list(map(str,cmd)))
  (exe.parent/'compile.json').write_text(json.dumps({'commands':commands,'object_sha256':sha(obj),'executable_sha256':sha(exe)},indent=2)+'\n')
  return
 binding=_canonical_observation(ROOT,obj,exe,a.integration,str(SOURCE.relative_to(ROOT)),providers=('uc-library/src/Presonus/DspComponent.cpp',))
 data=json.loads((HERE/'fixtures.json').read_text());nm=run(['/usr/bin/nm','--defined-only',obj]);assert data['mangled'] in {l.split()[-1] for l in nm.splitlines() if l.split()}
 actual=run([exe],input=''.join(str(c['input_bits'])+'\n' for c in data['cases']))
 rows=[list(map(int,l.split())) for l in actual.splitlines()];assert rows==[[c['input_bits'],c['result']] for c in data['cases']],(rows,data['cases'])
 run([FMT,'--style=file','--fallback-style=LLVM','--dry-run','--Werror',HEADER,SOURCE,HERE/'Replay.cpp'])
 paths=[HEADER,SOURCE,ROOT/'uc-library/src/Presonus/DspComponent.cpp',ROOT/'uc-library/include/presonus/DspComponent.hpp',HERE/'Replay.cpp',HERE/'native.py',HERE/'check.py',HERE/'fixtures.json',ROOT/'third_party/ccl-framework/core/portable/corecomponent.cpp',ROOT/'third_party/ccl-framework/core/portable/coreparams.cpp']
 # Transitive dependencies from actual local production/replay compile commands.
 deps=set()
 for dep in ([] if binding is not None else [Path(str(BUILD/'FX.o')+'.d'),Path(str(BUILD/'FXReplay')+'.d')]):
  if dep.exists():
   for token in dep.read_text().replace('\\\n',' ').split()[1:]:
    q=Path(token);q=q if q.is_absolute() else ROOT/q
    if q.is_file() and q.is_relative_to(ROOT):deps.add(q)
 if binding is not None:deps.update(ROOT/p for p in binding['files'])
 paths=sorted(set(paths)|deps)
 source_bindings={str(q.relative_to(ROOT)):sha(q) for q in paths}
 domain='15 finite binary32 inputs in signed int32 range including negative fractions, signed zero, positive fractions and both representable integer endpoints; actual CCL NumericParam set/get bits and C++ return compared with original ARM instruction/libgcc observations. Parameter getValue native body is a recorded boundary stub; no receiver/nonstack writes.'
 row={'original_elf_sha256':data['original_elf_sha256'],'mangled':data['mangled'],'sources':{str(q.relative_to(ROOT/'uc-library')):sha(q) for q in paths if q.is_relative_to(ROOT/'uc-library')},'repository_sources':{str(q.relative_to(ROOT)):sha(q) for q in paths if q.is_relative_to(ROOT/'third_party')},'domain':domain,'portable_ready':False,'cpp_compiled':True,'mangling_namespace_checked':True,'declaration_uncertainties':['Original unencoded return declaration unresolved; source-port signed int32 chosen from native conversion.','Original class layout/inheritance and ARM ABI unresolved.']}
 proof={'version':1,'task_id':TASK,'session_id':'01a1e2e7-862b-78c3-9f29-e8aad84be223','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'functions':[dict(row,case_count=len(rows),original_range=data['original_range'],cpp_differential_passed=True)],'proposed_readiness':{'ready':[],'pending':[row]},'cpp_compiled':True,'cpp_differential_passed':True,'compiled_mangled_names_matched':True,'original_arm_abi_verified':False,'hardware_verified':False,'source_bindings':source_bindings,'native_fixture_sha256':sha(HERE/'fixtures.json'),'formatter':run([FMT,'--version']).strip(),'compiled_object':{'path':str(obj),'sha256':sha(obj)},'executable':{'path':str(exe),'sha256':sha(exe)},'canonical_integration_completed':False,'limitations':row['declaration_uncertainties']}
 proof.update(_canonical_fields(binding))
 if a.integration!='none':proof['fresh_integration_reference']={'path':str(Path(a.integration).resolve()),'sha256':sha(a.integration)}
 out=Path(a.out).resolve();out.parent.mkdir(parents=True,exist_ok=True)
 assert not out.is_relative_to(ROOT/'uc-library/candidates') and out not in paths,'Never overwrite bound proof/input'
 if out.exists():
  previous=out.read_bytes();history=out.with_name(out.stem+'.previous-'+hashlib.sha256(previous).hexdigest()+out.suffix)
  if history.exists():assert history.read_bytes()==previous
  else:history.write_bytes(previous)
 out.write_text(json.dumps(proof,indent=2)+'\n');print('PASS',TASK,len(rows))
if __name__=='__main__':main()
