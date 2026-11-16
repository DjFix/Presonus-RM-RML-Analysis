"""Phase07 four-option supplied-binary canonical replay; compilation is explicit only."""
import argparse,datetime,hashlib,json,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];C=Path('/home/rs/projects/opencs/ai-line-analysis');PYTHON=C/'uc-library/.venv/bin/python';FMT=C/'uc-library/.venv/bin/clang-format';BUILD=C/'temp/core-upstream/root-integration-01';SDK=BUILD/'upstream-core/sdk/lib'
CONFIG={'04':('GlobalComponent','StoreReplay',['uc-library/src/Presonus/Mixer/MixerComponentBase.cpp'],[]),'07':('FXComponent','FXLoadReplay',['uc-library/src/Presonus/DspComponent.cpp'],['uc-library/include/presonus/DspComponent.hpp']),'10':('ParamLink','ConnectReplay',['uc-library/src/Presonus/Mixer/ControlMapping.cpp','uc-library/src/Presonus/MixerClientComponentBase.cpp','uc-library/src/mixer_state/MixerState.cpp'],['uc-library/include/presonus/mixer/ControlMapping.hpp','uc-library/include/presonus/MixerClientComponentBase.hpp','uc-library/include/presonus/mixer_state/MixerState.hpp'])}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(argv,**kw):
 start=datetime.datetime.now(datetime.timezone.utc);r=subprocess.run(list(map(str,argv)),text=True,capture_output=True,**kw);assert r.returncode==0,(list(map(str,argv)),r.stdout,r.stderr);return r.stdout,dict(argv=list(map(str,argv)),utc=start.isoformat(),seconds=(datetime.datetime.now(datetime.timezone.utc)-start).total_seconds(),returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)
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

def main(default=None):
 p=argparse.ArgumentParser();p.add_argument('--exe',required=True);p.add_argument('--object',required=True);p.add_argument('--integration',required=True);p.add_argument('--out',required=True);p.add_argument('--compile',action='store_true');p.add_argument('--task',default=default or Path(__file__).parent.name);a=p.parse_args();task=a.task;key=task[-2:];cls,_,helpers,headers=CONFIG[key];here=ROOT/'uc-library/tests/recovery'/task;source=ROOT/'uc-library/src/Presonus/Mixer'/(cls+'.cpp');header=ROOT/'uc-library/include/presonus/mixer'/(cls+'.hpp');exe=Path(a.exe).resolve();obj=Path(a.object).resolve();data=json.loads((here/'fixtures.json').read_text());commands=[]
 flags=['-std=c++17','-DCORE_USE_OPENSSL=1','-DNDEBUG=1','-DPRESONUS_HAS_UPSTREAM_CORE=1','-I'+str(ROOT/'uc-library/include'),'-isystem',str(ROOT/'third_party/ccl-framework'),'-O3','-Wall','-Wextra','-Wpedantic','-pthread','-Ulinux']
 if a.compile:
  exe.parent.mkdir(parents=True,exist_ok=True);obj.parent.mkdir(parents=True,exist_ok=True)
  extra=[ROOT/x for x in helpers] if key!='04' else [BUILD/'libpresonus_rm_components.a']
  libs=[SDK/'libcorelib.a',SDK/'libpresonus_core_allocator.a']
  if key=='04':libs += ['/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lz','-lssl','-lcrypto','-ldl',BUILD/'private-glibc29-provider/libpresonus_private_glibc29.a','-lm']
  else:libs+=['-ldl']
  for argv in [['/usr/bin/c++',*flags,'-MD','-MF',str(obj)+'.d','-c',source,'-o',obj],['/usr/bin/c++',*flags,'-fno-rtti','-MD','-MF',str(exe)+'.d',here/'Replay.cpp',obj,*extra,*libs,'-o',exe]]:
   _,log=run(argv);commands.append(log)
  Path(str(exe)+'.compile.json').write_text(json.dumps(commands,indent=2)+'\n');return
 binding=_canonical_observation(ROOT,obj,exe,a.integration,str(source.relative_to(ROOT)),providers=tuple(helpers),archives=('libcorelib.a','libpresonus_core_allocator.a'))
 names,log=run(['/usr/bin/nm','--defined-only',obj]);commands.append(log);assert data['mangled'] in {l.split()[-1] for l in names.splitlines() if l.split()}
 if key=='04':stdin=''.join(f"{c['filter']} {c['save_result']}\n" for c in data['cases'])
 elif key=='07':stdin=''.join(' '.join(map(str,[c['filter'],c['result'],*c['values']]))+'\n' for c in data['cases'])
 else:stdin=''.join(' '.join(map(str,[c['source'],c['flag'],c['found'],c['client'],c['old']]))+'\n' for c in data['cases'])
 argv=[exe]
 if key=='04':
  # Unique project-local task output, never system temporary storage.
  scratch=ROOT/'temp/test-work';scratch.mkdir(parents=True,exist_ok=True);argv.append(tempfile.mkdtemp(prefix=task+'-',dir=scratch))
 output,log=run(argv,input=stdin);commands.append(log);rows=[line.split()[1:] for line in output.splitlines() if line.startswith('ROW ')];assert len(rows)==len(data['cases'])
 for row,c in zip(rows,data['cases']):
  if key=='04':
   assert list(map(int,row[:3]))==[int('save' in c['calls']),1,0] and int(row[3])>0
   case_index=data['cases'].index(c);files=list((Path(argv[1])/str(case_index)).rglob('mixer.scene'));assert len(files)==1
   payload=json.loads(files[0].read_text());assert payload==({} if c['filter'] else {'gain':4.5}),payload
  elif key=='07':assert list(map(int,row))==[c['return'],1,0,1]
  else:
   target=c['target'];assert list(map(float,row))==[target,0,int(target and c['flag']),4.5 if target and c['source'] else 0.,4.5],(row,c)
 _,log=run([FMT,'--style=file','--fallback-style=LLVM','--dry-run','--Werror',header,source,here/'Replay.cpp']);commands.append(log)
 paths={header,source,here/'Replay.cpp',here/'native.py',here/'check.py',here/'fixtures.json',ROOT/'uc-library/tests/recovery/real10_g06_s04/native.py',ROOT/'uc-library/tests/recovery/real10_g06_s04/check.py'}|{ROOT/x for x in helpers+headers}
 providers=['corecomponent.cpp','corecomponent.h','coreparams.cpp','coreparams.h','corestorage.h','corepersistence.cpp','corepersistence.h','coreattributes.cpp','coreattributes.h','corefile.cpp','corefile.h']
 paths|={ROOT/'third_party/ccl-framework/core/portable'/x for x in providers};paths.add(ROOT/'third_party/ccl-framework/core/public/corevector.h')
 for dep in ([] if binding is not None else [Path(str(obj)+'.d'),Path(str(exe)+'.d')]):
  if dep.exists():
   for token in dep.read_text().replace('\\\n',' ').split()[1:]:
    q=Path(token);q=q if q.is_absolute() else ROOT/q
    if q.is_file() and q.is_relative_to(ROOT):paths.add(q)
 if binding is not None:paths.update(ROOT/p for p in binding['files'])
 binds={str(q.relative_to(ROOT)):sha(q) for q in sorted(paths)}
 domains={'04':'4 filter/null and producer success/failure combinations; native save/archive call argument/order and actual CCL archive queue file roundtrip, actual attribute filter and path composition.','07':'8 filter/null, load result0/1, two finite diagnostic float triples; original adapted mode/attribute/filter/loading-flag transitions, native f2d and return; real canonical DspComponent and actual CCL InputStorage/parameters observed.','10':'32 numeric-domain combinations source null/non-null, observer flag, lookup hit/miss, client null/non-null, old target; original receiver target writes and call branches; actual CCL lookup, setValue false, observer count, prior-observer removal and borrowed parameter preservation.'}
 limits=['Unencoded original declarations/class layouts/ARM ABI/hardware remain unverified. Explicit typed portable provider composition does not claim original inheritance.','Native named Core/provider/virtual boundaries are explicit test stubs; actual host providers executed separately. No Core binary recovery.','No EH, concurrency or allocation-failure testing.']
 if key=='07':limits+=['Real CCL Component base requires bool load; native retained-return comparison domain is0/1. App Dsp provider result outside0/1 and diagnostic NaN/infinity excluded.']
 if key=='10':limits+=['String-source connect and helper callback forwarding excluded from this numeric-domain proof; unbound non-null client identity outside valid portable domain throws explicitly.']
 row=dict(original_elf_sha256=data['original_elf_sha256'],mangled=data['mangled'],sources={str(q.relative_to(ROOT/'uc-library')):sha(q) for q in paths if q.is_relative_to(ROOT/'uc-library')},repository_sources={str(q.relative_to(ROOT)):sha(q) for q in paths if q.is_relative_to(ROOT/'third_party')},domain=domains[key],portable_ready=False,cpp_compiled=True,mangling_namespace_checked=True,declaration_uncertainties=limits[:1])
 proof=dict(version=1,task_id=task,session_id='01a1e2e7-862b-78c3-9f29-e8aad84be223',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),functions=[dict(row,original_range=data['original_range'],case_count=len(rows),cpp_differential_passed=True)],proposed_readiness=dict(ready=[],pending=[row]),cpp_compiled=True,cpp_differential_passed=True,compiled_mangled_names_matched=True,source_bindings=binds,commands=commands,original_arm_abi_verified=False,hardware_verified=False,limitations=limits,formatter=run([FMT,'--version'])[0].strip(),compiled_object=dict(path=str(obj),sha256=sha(obj)),executable=dict(path=str(exe),sha256=sha(exe)),canonical_integration_completed=False)
 proof.update(_canonical_fields(binding))
 if binding is not None:proof['provider_archives']={p['path']:p['sha256'] for p in binding['link']['archives']}
 if a.integration!='none':proof['fresh_integration_reference']=dict(path=str(Path(a.integration).resolve()),sha256=sha(a.integration))
 out=Path(a.out).resolve();assert out not in paths and not out.is_relative_to(ROOT/'uc-library/candidates'),'Never overwrite a bound proof/input';out.parent.mkdir(parents=True,exist_ok=True)
 if out.exists():
  previous=out.read_bytes();history=out.with_name(out.stem+'.previous-'+hashlib.sha256(previous).hexdigest()+out.suffix)
  if not history.exists():history.write_bytes(previous)
  else:assert history.read_bytes()==previous
 out.write_text(json.dumps(proof,indent=2)+'\n');print(task,'PASS',len(rows))
if __name__=='__main__':main()
