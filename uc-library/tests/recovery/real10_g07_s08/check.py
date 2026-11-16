import json,subprocess,sys,hashlib,os
from pathlib import Path
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent
BUILD=R/'temp/recovery-work/real10_g07/s08';BUILD.mkdir(parents=True,exist_ok=True)
CAN=Path('/home/rs/projects/opencs/ai-line-analysis');LIB=CAN/'temp/core-upstream/root-integration-01'
CPP='uc-library/src/Presonus/Panel/ChannelPresetComponent.cpp';HPP='uc-library/include/presonus/panel/ChannelPresetComponent.hpp';DRIVER=str(T.relative_to(R)/'Replay.cpp')
FLAGS=['-std=c++20','-O3','-DNDEBUG','-DNDEBUG=1','-DCORE_USE_OPENSSL=1','-DPRESONUS_HAS_UPSTREAM_CORE=1','-Wall','-Wextra','-Wpedantic','-pthread','-Ulinux','-fno-lto','-fno-fast-math','-ffp-contract=off','-fno-rtti','-Iuc-library/include','-Ithird_party/ccl-framework']
COMPILE=['/usr/bin/c++',*FLAGS,'-MMD','-MF',str(BUILD/'production.d'),'-c',CPP,'-o',str(BUILD/'production.o')]
LINK=['/usr/bin/c++',*FLAGS,'-MMD','-MF',str(BUILD/'replay.d'),DRIVER,str(BUILD/'production.o'),str(LIB/'libpresonus_rm_components.a'),str(LIB/'upstream-core/sdk/lib/libcorelib.a'),str(LIB/'upstream-core/sdk/lib/libpresonus_core_allocator.a'),'/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lz','-lssl','-lcrypto',str(CAN/'temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so'),str(LIB/'private-glibc29-provider/libpresonus_private_glibc29.a'),'-ldl','-lm','-o',str(BUILD/'replay')]
def run(argv,**kw):
 print(json.dumps(list(map(str,argv))),flush=True);p=subprocess.run(list(map(str,argv)),cwd=R,text=True,capture_output=True,timeout=120,env={**os.environ,'TMPDIR':str(BUILD)},**kw)
 if p.returncode:print(p.stdout+p.stderr);p.check_returncode()
 return p

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

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('mode',nargs='?',default='proof');p.add_argument('--exe');p.add_argument('--object');p.add_argument('--integration');p.add_argument('--out');a=p.parse_args()
 if a.mode=='compile':run(COMPILE);run(LINK)
 elif a.mode=='format':run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',CPP,HPP,DRIVER])
 elif a.mode=='symbols':
  out=run(['/usr/bin/nm','--defined-only',a.object or BUILD/'production.o']).stdout;assert '_ZN8Presonus5Panel22ChannelPresetComponent23onPresetCategoryChangedEv' in {x.split()[-1] for x in out.splitlines()}
 else:
  exe=Path(a.exe or BUILD/'replay');obj=Path(a.object or BUILD/'production.o');assert exe.is_file() and obj.is_file()
  binding=_canonical_observation(R,obj,exe,a.integration,CPP)
  data=json.loads((T/'fixtures.json').read_text());import native
  assert data['elf_sha256']==native.SHA and data['range']==native.RANGE
  for row in data['cases']:
   fresh=native.execute(row['input']);assert {k:fresh[k] for k in ['projection','trace']}==row['output']
  inputs=''
  for row in data['cases']:
   c=row['input'];inputs+=' '.join([str(int(c['gate_present'])),str(c['gate_bits']),json.dumps(c['selected']),*[json.dumps(x) for x in c['categories']]])+'\n'
  result=run([exe],input=inputs);lines=result.stdout.splitlines();assert len(lines)==len(data['cases'])
  for row,line in zip(data['cases'],lines):
   expected=row['output']['projection'];assert list(map(int,line.split()))==[expected['slot'],len(expected['search'])],(row['input'],line,expected)
  symbols=run(['/usr/bin/nm','--defined-only',obj]).stdout;assert native.NAME in {x.split()[-1] for x in symbols.splitlines()}
  proof=dict(success=True,case_count=len(lines),domain='44 ARM/portable comparisons: missing gate, signed zeros, negative, fractional positive, NaN, infinity, subnormal, no match/first/middle/last and bounded CString32 truncation; slot and number of category reads',originals=[data['range']],executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),object_sha256=hashlib.sha256(obj.read_bytes()).hexdigest(),integration=a.integration)
  source_paths=[CPP,HPP,DRIVER,str(T.relative_to(R)/'check.py'),str(T.relative_to(R)/'native.py')]
  source_hashes={x.removeprefix('uc-library/'):hashlib.sha256((R/x).read_bytes()).hexdigest() for x in source_paths[:2]}
  dependencies={}
  for dep in ([] if binding is not None else [BUILD/'production.d',BUILD/'replay.d']):
   if dep.exists():
    for name in dep.read_text().replace('\\\n',' ').split(':',1)[1].split():
     path=Path(name);path=path if path.is_absolute() else R/path
     if path.is_file():dependencies[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
  if binding is not None:dependencies.update(binding['files'])
  proof.update(elf_sha256=native.SHA,producer_hashes={str(T.relative_to(R)/name):hashlib.sha256((T/name).read_bytes()).hexdigest() for name in ['native.py','check.py','Replay.cpp','fixtures.json']},formatter=run(['uc-library/.venv/bin/clang-format','--version']).stdout.strip(),compile_dependencies=dependencies,proposed_readiness={'ready':[],'pending':[{'original_elf_sha256':native.SHA,'mangled':native.NAME,'sources':source_hashes,'cpp_compiled':True,'mangling_namespace_checked':True,'portable_ready':False,'declaration_uncertainties':['Original ordinary return declaration is unencoded; portable void selected. Original receiver fields/layout/inheritance and ARM ABI remain unresolved.'],'validation_domain':proof['domain'],'repository_sources':{k[k.index('third_party/ccl-framework/'):]:v for k,v in dependencies.items() if 'third_party/ccl-framework/' in k}}]})
  proof.update(_canonical_fields(binding))
  if a.out:Path(a.out).write_text(json.dumps(proof,indent=2)+'\n')
  print(json.dumps(proof))
