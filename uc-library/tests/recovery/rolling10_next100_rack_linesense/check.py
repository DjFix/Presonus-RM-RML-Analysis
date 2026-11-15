"""Current-source worker and canonical native/provider replay; no shared writes."""
import argparse,datetime,hashlib,json,os,subprocess,time,shlex
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];BASE=Path(__file__).resolve().parent;TASK=BASE.name;CASE=2
PREFIX=Path('temp/recovery-work/rolling10x10-20261114/prepared-next-flow01');PACKET=PREFIX/'packets'/TASK;SNAPSHOT=Path('/home/rs/projects/opencs/ai-line-analysis')/PREFIX/'snapshot'
OUT=Path('temp/recovery-work')/TASK;PROOF=Path('uc-library/candidates')/TASK/'worker-proof.json'
NAMES=['alert_string','rack_linesense','mixsettings_paramchanged','channel_local_source','channel_external_source','monitor_apply','surfaceinput_setlevel']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('mode',nargs='?',default='replay')
 for name in ('exe','object','integration','out'):ap.add_argument('--'+name)
 args=ap.parse_args();os.chdir(ROOT);OUT.mkdir(parents=True,exist_ok=True);logs=[]
 def run(argv,**kw):
  start=time.monotonic();r=subprocess.run(list(map(str,argv)),text=True,capture_output=True,**kw);record=dict(argv=list(map(str,argv)),returncode=r.returncode,stdout=r.stdout,stderr=r.stderr,seconds=time.monotonic()-start);logs.append(record);print(json.dumps(record),flush=True);r.check_returncode();return r.stdout
 request=json.loads((PACKET/'request.json').read_text());t=request['targets'][0];owned=request['owned_files'];source=next(p for p in owned if '/src/' in p and p.endswith('.cpp'));replay=f'uc-library/tests/recovery/{TASK}/Replay.cpp'
 group=set()
 for name in NAMES:
  rr=json.loads((PREFIX/'packets'/('rolling10_next100_'+name)/'request.json').read_text());group.update(p for p in rr['owned_files'] if ('/include/' in p or '/src/' in p) and p.endswith(('.cpp','.hpp')))
 paths=sorted(group)+[replay];exe=Path(args.exe) if args.exe else OUT/'Replay';obj=Path(args.object) if args.object else OUT/'target.o'
 flags=['g++','-std=c++17','-O2','-fno-rtti','-ffunction-sections','-fdata-sections','-Wno-multichar','-Iuc-library/include','-isystem','third_party/ccl-framework']
 extras=[]
 if CASE==2:extras=['uc-library/src/Presonus/Mixer/MixerComponentBase.cpp','uc-library/src/Presonus/Mixer/ChannelComponent.cpp']
 if CASE==7:extras=['uc-library/src/Presonus/Surface/SurfaceChannelComponent.cpp']
 sdk='/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk/lib/';archives=[sdk+'libcorelib.a',sdk+'libpresonus_core_allocator.a']
 if args.mode=='format':run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror']+paths);return
 if args.mode=='compile':
  run(flags+['-c',source,'-o',obj]);run(flags+[replay,obj]+extras+['-Wl,--gc-sections']+archives+['-pthread','-ldl','-lz','-o',exe]);deps=set(group)
  for cpp in [source,replay]+extras:
   output=run(flags+['-M',cpp]);deps.update(p for p in output.replace('\\\n',' ').split()[1:] if p.startswith(('uc-library/','third_party/ccl-framework/')))
  (OUT/'dependencies.json').write_text(json.dumps({p:sha(p) for p in sorted(deps)},indent=2));(OUT/'compilation.json').write_text(json.dumps(logs,indent=2));return
 sym=run(['nm','--defined-only',obj]);assert t['mangled'] in {line.split()[-1] for line in sym.splitlines() if line.split()}
 if args.mode=='symbols':return
 from native import generate
 fixture=json.loads((BASE/'fixtures.json').read_text());assert generate(exe)==fixture
 if args.mode=='native':return
 run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror']+paths)
 for case in fixture['cases']:
  actual=run([str(exe.resolve())],input=' '.join(map(str,case['inputs']))+'\n').strip();assert actual==case['expected'],(case['inputs'],actual,case['expected'])
 if args.exe or args.object:
  assert args.exe and args.object, 'Canonical supplied-output mode requires both --exe and --object'
  build=next((p for p in obj.resolve().parents if (p/'compile_commands.json').is_file()),None)
  assert build is not None, 'Canonical compile_commands.json not found for supplied object'
  compile_db=build/'compile_commands.json';entries=json.loads(compile_db.read_text());dependencies={p:sha(p) for p in sorted(group)};observed_commands=[];dependency_scans=[];sdk_observations=[]
  readmap=json.loads((ROOT/'temp/recovery-work/rolling10x10-20261114/READ_INPUTS-prepared-next-flow01-rolling10_pages.json').read_text());provider_bindings=[]
  for relative in request['declared_source_dependencies']:
   if relative.startswith('third_party/ccl-framework/core/'):
    sealed=readmap[relative];expected=sealed['sha256'];assert sha(ROOT/relative)==expected and sha(sealed['frozen_read_path'])==expected
    dependencies[relative]=expected;provider_bindings.append(dict(path=relative,sha256=expected,frozen_read_path=sealed['frozen_read_path'],scope='Graph-bound declared pinned provider, not inferred from installed path'))
  def entry_directory(entry):
   directory=Path(entry['directory']);return directory if directory.is_absolute() else (build/directory).resolve()
  def entry_source(entry):
   path=Path(entry['file']);return (path if path.is_absolute() else entry_directory(entry)/path).resolve()
  for cpp in [source,replay]+extras:
   source_path=(ROOT/cpp).resolve();matches=[x for x in entries if entry_source(x)==source_path]
   assert len(matches)==1, ('Canonical compile command must be unique',cpp,len(matches))
   entry=matches[0];argv=entry.get('arguments') or shlex.split(entry['command']);filtered=[];i=0
   while i<len(argv):
    token=argv[i]
    if token in ('-o','-MF','-MT','-MQ'):i+=2;continue
    if token in ('-c','-MD','-MMD','-MP'):i+=1;continue
    token_path=Path(token);token_path=token_path if token_path.is_absolute() else entry_directory(entry)/token_path
    if token_path.resolve()==source_path:i+=1;continue
    filtered.append(token);i+=1
   # Exact production/driver flags, dependency-only scan: no recompilation,
   # object overwrite or claim that this producer executed the recorded build.
   scan=filtered+['-M',str(source_path)];output=run(scan,cwd=entry_directory(entry));dependency_scans.append(dict(argv=scan,directory=str(entry_directory(entry))))
   observed_commands.append(entry)
   for token in output.replace('\\\n',' ').split(':',1)[1].split():
    path=Path(token);path=path if path.is_absolute() else entry_directory(entry)/path;path=path.resolve()
    if path.is_file() and path.is_relative_to(ROOT):
     relative=str(path.relative_to(ROOT))
     if relative.startswith(('uc-library/','third_party/ccl-framework/core/')):dependencies[relative]=sha(path)
     sdk_root=build/'upstream-core/sdk/include/presonus-core-5'
     if path.is_relative_to(sdk_root/'core'):
      candidate=Path('third_party/ccl-framework')/path.relative_to(sdk_root);pinned=ROOT/candidate;digest=sha(path)
      # Map only actual byte-identical files; retain both physical identities.
      assert pinned.is_file() and sha(pinned)==digest, ('Installed Core header differs from pinned source',str(path),str(pinned))
      if str(candidate) in readmap:assert readmap[str(candidate)]['sha256']==digest
      dependencies[str(candidate)]=digest;sdk_observations.append(dict(installed_path=str(path),installed_sha256=digest,pinned_path=str(candidate),pinned_sha256=digest,scope='Exact current installed-header/pinned-source byte identity; no original ABI or historical build attribution'))
  compilation_records=[]
  compilation_provenance=dict(kind='supplied_canonical_outputs',compile_commands=dict(path=str(compile_db),sha256=sha(compile_db)),observed_build_commands=observed_commands,declared_provider_bindings=provider_bindings,installed_sdk_observations=sdk_observations,executed_dependency_only_scans=dependency_scans,local_compilation_executed_by_producer=False,object=dict(path=str(obj.resolve()),sha256=sha(obj)),executable=dict(path=str(exe.resolve()),sha256=sha(exe)))
 else:
  dependencies=json.loads((OUT/'dependencies.json').read_text());assert all(sha(p)==d for p,d in dependencies.items()),'Compile dependency changed'
  compilation_records=json.loads((OUT/'compilation.json').read_text())
  compilation_provenance=dict(kind='worker_local_compile_receipt',path=str(OUT/'compilation.json'),sha256=sha(OUT/'compilation.json'),local_compilation_executed_by_producer=False,note='Historical compile receipt belongs to compile mode, not this replay invocation')
 bindings={p:sha(p) for p in sorted(group)}
 bindings.update({str(BASE.relative_to(ROOT)/name):sha(BASE/name) for name in ('Replay.cpp','check.py','native.py','fixtures.json')});bindings.update(dependencies)
 sources={str(Path(p).relative_to('uc-library')):d for p,d in bindings.items() if p.startswith('uc-library/')};providers={p:d for p,d in bindings.items() if p.startswith('third_party/ccl-framework/core/')}
 typed=request['reconstruction_contract'];cp=SNAPSHOT/typed['path'];assert sha(cp)==typed['sha256'];contract=json.loads(cp.read_text());evidence={}
 for gr in list(contract['requirements'].values())+contract['dependencies']:
  for ref in gr.get('evidence',[]):
   p=SNAPSHOT/ref['path'];assert sha(p)==ref['sha256'];evidence[str(p)]=ref['sha256']
 limits=['Original ordinary return declaration, complete class inheritance/layout, ARM ABI and hardware behavior remain unresolved.','Actual CCL source-provider composition/inheritance and typed ARM-to-host RPC are intentional source ports; no Core binary code executed.','Finite stable metadata/registry domains only; no callback mutation, allocation failure, exception or concurrency claims.','Native call arguments/order recorded; C++ actual provider effects/events compared, C++ provider call order additionally reviewed from source.']
 if CASE==1:limits.append('Original C++ RTTI dynamic_cast replaced by actual pinned StringParam::cast type-ID dispatch; no original RTTI equivalence claim.')
 entry=dict(original_elf_sha256=t['original_elf_sha256'],mangled=t['mangled'],sources=sources,repository_sources=providers,domain=fixture['domain'],portable_ready=False,cpp_compiled=True,mangling_namespace_checked=True,declaration_uncertainties=limits)
 proof=dict(version=1,task_id=TASK,producer_session_id=os.environ.get('CODEX_THREAD_ID'),created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),functions=[entry],proposed_readiness=dict(canonical_binding_pending=args.integration is None,ready=[],pending=[entry]),source_bindings=bindings,typed_contract=dict(path=str(cp),sha256=sha(cp)),typed_evidence=evidence,original_range={k:fixture[k] for k in ('elf_sha256','address','size','section','file_offset','range_sha256')},native_ranges=fixture['verified_ranges'],fixture_sha256=sha(BASE/'fixtures.json'),case_count=len(fixture['cases']),commands=logs,compilation=compilation_records,compilation_provenance=compilation_provenance,provider_archives={p:sha(p) for p in archives},cpp_compiled=True,compiled_mangled_names_matched=True,cpp_differential_passed=True,portable_ready=False,original_arm_abi_verified=False,hardware_verified=False,limitations=limits,executable=dict(path=str(exe),sha256=sha(exe)),object=dict(path=str(obj),sha256=sha(obj)),tools=dict(formatter=run(['uc-library/.venv/bin/clang-format','--version']).strip(),compiler=run(['g++','--version']).splitlines()[0]))
 proof['canonical_producer_revision']=dict(current_sha256=sha(BASE/'check.py'),historical_worker_producer_sha256='a795a53c7e2fca1c6070f8de090b20c3ae74cea94d00861605a56d5adf949da5',scope='Explicit canonical-only producer revision; worker HANDOFF/proof/producer bytes stay frozen and are not relabeled as this producer')
 if args.integration:proof['integration']=dict(path=args.integration,sha256=sha(args.integration))
 dest=Path(args.out) if args.out else PROOF;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(proof,indent=2)+'\n');print(TASK,len(fixture['cases']),'native/provider cases passed')
if __name__=='__main__':main()
