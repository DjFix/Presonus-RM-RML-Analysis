"""Fresh original/native/provider differential and current-output proof producer."""
import argparse,datetime,hashlib,json,os,pathlib,subprocess,time,shlex
ROOT=pathlib.Path(__file__).resolve().parents[4];NAME=pathlib.Path(__file__).parent.name
NAMES=['rolling10_next_mixer_base_04','rolling10_typed_subgroup_01','rolling10_typed_digital_refresh_01','rolling10_next100_count_solos','rolling10_next100_set_channel_params','rolling10_next100_tdm_routes'];K=NAMES.index(NAME)+1
TEST=pathlib.Path('uc-library/tests/recovery')/NAME;S=pathlib.Path('temp/recovery-work')/NAME;GROUP=pathlib.Path('temp/recovery-work/phasea-mixer');PACKET=pathlib.Path('temp/recovery-work/rolling10x10-20261114/prepared-remaining14-phasea-proposed01/packets')/NAME
HEADER='uc-library/include/presonus/mixer/MixerComponentBase.hpp';SOURCE='uc-library/src/Presonus/Mixer/MixerComponentBase.cpp';EXTRA='uc-library/src/Presonus/Mixer/ChannelComponent.cpp';CPP=[HEADER,SOURCE,str(TEST/'Replay.cpp')]
FLAGS=['/usr/bin/c++','-std=c++17','-O2','-fno-rtti','-DNDEBUG=1','-DCORE_USE_OPENSSL=1','-DPRESONUS_HAS_UPSTREAM_CORE=1','-Ulinux','-Wno-multichar','-ffunction-sections','-fdata-sections','-fno-fast-math','-ffp-contract=off','-pthread','-Iuc-library/include','-Ithird_party/ccl-framework']
LIBS=['-Wl,--start-group',str(GROUP/'core-build/artifacts/linux/Release/libcorelib.a'),str(GROUP/'core-build/libpresonus_core_allocator.a'),'-Wl,--end-group','-lz','-lssl','-lcrypto','-ldl','-lm']
def digest(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def run(argv,**kwargs):
 t=time.monotonic();argv=list(map(str,argv));p=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True,env={**os.environ,'TMPDIR':str(ROOT/S)},**kwargs);d=dict(argv=argv,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr,seconds=time.monotonic()-t)
 if p.returncode:raise RuntimeError(json.dumps(d))
 return d
def compile_local():
 receipt=json.loads((ROOT/GROUP/'CORE_BUILD_RECEIPT.json').read_text());assert receipt['pinned_commit']=='e8cbdea4a4a20e15111f5a690798a259c0374b31' and not receipt['historical_archives_reused']
 for p,h in receipt['archives'].items():assert digest(p)==h
 records=[]
 for src,obj in [(SOURCE,'production.o'),(EXTRA,'channel.o')]:records.append(run(FLAGS+['-MMD','-MF',S/(obj+'.d'),'-c',src,'-o',S/obj]))
 for provider in [True,False]:
  records.append(run(FLAGS+[f'-DTASK_KIND={K}',*(['-DPROVIDER_ONLY=1'] if provider else []),'-MMD','-MF',S/('provider.d' if provider else 'replay.d'),str(TEST/'Replay.cpp'),str(S/'channel.o'),*([] if provider else [str(S/'production.o')]),'-Wl,--gc-sections',*LIBS,'-o',S/('provider' if provider else 'replay')]))
 (ROOT/S/'compilation.json').write_text(json.dumps(records,indent=2)+'\n');return records

def replay(exe):
 import native
 f=json.loads((ROOT/TEST/'fixtures.json').read_text());payload='\n'.join(native.line(c['input']) for c in f['cases'])+'\n';r=run([exe],input=payload);actual=r['stdout'].splitlines();expected=[c['expected'] for c in f['cases']];assert len(actual)==len(expected),(len(actual),len(expected))
 for j,(a,e) in enumerate(zip(actual,expected)):assert a==e,(j,f['cases'][j],a,e)
 return {'cases':len(expected),'native_cases':len(expected),'cpp_differential_passed':True,'input_sha256':hashlib.sha256(payload.encode()).hexdigest(),'observed_output_sha256':hashlib.sha256(r['stdout'].encode()).hexdigest(),'domain':f['scope'],'run':r}
def canonical_dependencies(exe,obj):
 objpath=(ROOT/obj).resolve(); build=next((p for p in objpath.parents if (p/'compile_commands.json').exists()),None)
 assert build is not None, 'supplied object must belong to actual canonical build with compile_commands.json'
 entries=json.loads((build/'compile_commands.json').read_text());observations=[];scans=[];paths=set()
 def directory(e):
  p=pathlib.Path(e['directory']);return p if p.is_absolute() else build/p
 def source(e):
  p=pathlib.Path(e['file']);return (p if p.is_absolute() else directory(e)/p).resolve()
 for requested in [SOURCE,EXTRA,str(TEST/'Replay.cpp')]:
  target=(ROOT/requested).resolve();matches=[e for e in entries if source(e)==target];assert len(matches)==1,(requested,len(matches))
  e=matches[0];argv=e.get('arguments') or shlex.split(e['command']);filtered=[];skip=False
  for token in argv:
   if skip:skip=False;continue
   if token in ['-o','-MF','-MT','-MQ']:skip=True;continue
   if token in ['-c','-MD','-MMD','-MP']:continue
   if token.startswith(('-MF','-MT','-MQ')):continue
   q=pathlib.Path(token)
   if not token.startswith('-') and (q if q.is_absolute() else directory(e)/q).resolve()==target:continue
   filtered.append(token)
  scanargv=filtered+['-M',str(target)];start=time.monotonic();p=subprocess.run(scanargv,cwd=directory(e),text=True,capture_output=True);assert p.returncode==0,p.stderr
  scans.append({'argv':scanargv,'directory':str(directory(e)),'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'seconds':time.monotonic()-start,'kind':'executed_dependency_only_no_object_rebuild'})
  observations.append({'entry':e,'source_sha256':digest(requested),'kind':'observed_current_compile_commands_entry_not_claimed_executed_build'})
  for token in shlex.split(p.stdout.replace('\\\n',' ').split(':',1)[1]):
   q=pathlib.Path(token);q=(q if q.is_absolute() else directory(e)/q).resolve()
   try:rel=str(q.relative_to(ROOT))
   except ValueError:continue
   if rel.startswith(('uc-library/','third_party/ccl-framework/')):paths.add(rel)
 req=json.loads((ROOT/PACKET/'request.json').read_text());provider_bindings=[]
 readmap=json.loads((ROOT/'temp/recovery-work/rolling10x10-20261114/READ_INPUTS-prepared-remaining14-phasea-proposed01-rolling10_mixer_base.json').read_text())
 for rel in req['declared_source_dependencies']:
  if rel.startswith('third_party/ccl-framework/'):
   binding=readmap[rel];assert digest(rel)==binding['sha256'];assert hashlib.sha256(pathlib.Path(binding['frozen_read_path']).read_bytes()).hexdigest()==binding['sha256'];paths.add(rel);provider_bindings.append({'path':rel,**binding,'kind':'declared_graph_bound_provider_source_verified_against_immutable_snapshot'})
 mappings=[];sdk=build/'upstream-core/sdk/include/presonus-core-5'
 for scan in scans:
  for token in shlex.split(scan['stdout'].replace('\\\n',' ').split(':',1)[1]):
   q=pathlib.Path(token);q=(q if q.is_absolute() else pathlib.Path(scan['directory'])/q).resolve()
   try:relative=q.relative_to(sdk)
   except ValueError:continue
   rel=str(pathlib.Path('third_party/ccl-framework')/relative);pinned=ROOT/rel
   if not pinned.is_file():continue
   installed=hashlib.sha256(q.read_bytes()).hexdigest();assert installed==digest(rel),(q,rel)
   if rel in readmap:assert readmap[rel]['sha256']==installed
   paths.add(rel);mappings.append({'installed_sdk_header':str(q),'pinned_repository_source':rel,'sha256':installed,'kind':'exact_matching_header_bytes_not_original_layout_or_ABI'})
 return sorted(paths),{'kind':'supplied_canonical_outputs','local_compilation_executed_by_producer':False,'observed_build_commands':observations,'executed_dependency_only_scans':scans,'declared_provider_bindings':provider_bindings,'exact_sdk_header_mappings':mappings,'compile_commands':{'path':str(build/'compile_commands.json'),'sha256':hashlib.sha256((build/'compile_commands.json').read_bytes()).hexdigest()},'executable_sha256':digest(exe),'object_sha256':digest(obj)}
def dependency_sources():
 paths={HEADER,SOURCE,EXTRA,str(TEST/'Replay.cpp')};
 for p in (ROOT/S).glob('*.d'):
  raw=p.read_text().replace('\\\n',' ');tokens=shlex.split(raw.split(':',1)[1]);
  for x in tokens:
   q=pathlib.Path(x);q=q if q.is_absolute() else ROOT/q
   try:rel=str(q.resolve().relative_to(ROOT))
   except ValueError:continue
   if rel.startswith(('uc-library/','third_party/ccl-framework/')):paths.add(rel)
 req=json.loads((ROOT/PACKET/'request.json').read_text());paths.update(req['declared_source_dependencies']);paths.update(json.loads((ROOT/GROUP/'CORE_BUILD_RECEIPT.json').read_text())['repository_source_closure']);return sorted(paths)
def proof(exe,obj,out,integration=None):
 import native
 req=json.loads((ROOT/PACKET/'request.json').read_text());t=req['targets'][0];fixture=json.loads((ROOT/TEST/'fixtures.json').read_text());format_check=run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*CPP]);symbols=run(['/usr/bin/nm','--defined-only',obj]);assert t['mangled'] in {l.split()[-1] for l in symbols['stdout'].splitlines() if l.split()};r=replay(exe);paths,compilation_provenance=canonical_dependencies(exe,obj) if SUPPLIED else (dependency_sources(),{'kind':'worker_compilation_receipt','local_compilation_executed_by_producer':False,'commands':json.loads((ROOT/S/'compilation.json').read_text()),'receipt_scope':'Actual previously executed worker commands embedded immutably in this proof; later acceptance recompilation is separately logged'});sources={p:digest(p) for p in paths if p.startswith('uc-library/')};repository_sources={p:digest(p) for p in paths if p.startswith('third_party/')};now=datetime.datetime.now(datetime.timezone.utc).isoformat();function={'original_elf_sha256':t['original_elf_sha256'],'mangled':t['mangled'],'cpp_compiled':True,'mangling_namespace_checked':True,'cpp_differential_passed':True,'portable_ready':False,'domain':'256 original ARM executions: 0/1/2/7 valid channels, tags -1/0/5/1001, missing/wrong/present tags, eight finite requested float values within/outside actual [-100,100] parameter range, varied initial states; actual source clamping and controller/observer identity/event order, edit=true.','declaration_uncertainties':['Original ordinary return, original inheritance/layout/ownership and ARM ABI remain unresolved. Explicit source-port facade/state/return choices; no hardware credit.']}
 d={'version':1,'task_id':NAME,'session_id':'01a1d7a9-96e0-7090-80ac-def2fe3c327f','produced_utc':now,'producer':{'path':str(TEST/'check.py'),'sha256':digest(TEST/'check.py')},'functions':[function],'sources':sources,'repository_sources':repository_sources,'cpp_differential_passed':True,'compiled_mangled_names_matched':True,'mangling_namespace_checked':True,'replay':r,'compilation_provenance':compilation_provenance,'native':{'elf_sha256':t['original_elf_sha256'],'ranges':fixture['ranges'],'producer':{'path':str(TEST/'native.py'),'sha256':digest(TEST/'native.py')},'fixture':{'path':str(TEST/'fixtures.json'),'sha256':digest(TEST/'fixtures.json')},'emulator_version':__import__('unicorn').__version__,'cases':len(fixture['cases']),'scope':fixture['scope']},'format':{'formatter_version':run(['uc-library/.venv/bin/clang-format','--version'])['stdout'].strip(),'check':format_check},'symbols':symbols,'compiler_version':run(['/usr/bin/c++','--version'])['stdout'].splitlines()[0],'executable':{'path':str(exe),'sha256':digest(exe)},'object':{'path':str(obj),'sha256':digest(obj)},'proposed_readiness':{'canonical_binding_pending':True,'ready':[],'pending':[{**function,'sources':{p.removeprefix('uc-library/'):h for p,h in sources.items()},'repository_sources':repository_sources}]},'remarks':[{'date':now,'original_elf_sha256':t['original_elf_sha256'],'mangled':t['mangled'],'status':'compiled_declaration_pending','observation':'256 original ARM executions: 0/1/2/7 valid channels, tags -1/0/5/1001, missing/wrong/present tags, eight finite requested float values within/outside actual [-100,100] parameter range, varied initial states; actual source clamping and controller/observer identity/event order, edit=true.','retry_condition':'Independent original declarations for promotion; new native/provider evidence for wider domains.'}]}
 if integration:d['integration']={'path':str(integration),'sha256':digest(integration)}
 if not SUPPLIED:
  d['canonical_replay_pending']=True;d['local_compile_commands']=json.loads((ROOT/S/'compilation.json').read_text());d['dependencies']={p:digest(p) for p in paths};d['provider_provenance']={'path':str(GROUP/'CORE_BUILD_RECEIPT.json'),'sha256':digest(GROUP/'CORE_BUILD_RECEIPT.json'),'scope':'Fresh actual pinned official Core source build; no historical app/provider archive substituted.'};d['provider_archives']=json.loads((ROOT/GROUP/'CORE_BUILD_RECEIPT.json').read_text())['archives'];d['provider_only_executable']={'path':str(S/'provider'),'sha256':digest(S/'provider')}
 (ROOT/out).parent.mkdir(parents=True,exist_ok=True);(ROOT/out).write_text(json.dumps(d,indent=2)+'\n');return d
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['compile','format','symbols','native','replay','proof']);p.add_argument('--exe',type=pathlib.Path);p.add_argument('--object',type=pathlib.Path);p.add_argument('--out',type=pathlib.Path);p.add_argument('--integration',type=pathlib.Path);a=p.parse_args();os.chdir(ROOT);(ROOT/S).mkdir(parents=True,exist_ok=True);exe=a.exe or S/'replay';obj=a.object or S/'production.o';SUPPLIED=bool(a.exe or a.object);assert not SUPPLIED or bool(a.exe and a.object),'supply both canonical executable and object'
 if a.mode=='compile':compile_local();print('Fresh current source/provider compilation passed')
 elif a.mode=='format':run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*CPP]);print('Format passed')
 elif a.mode=='symbols':
  t=json.loads((ROOT/PACKET/'request.json').read_text())['targets'][0];s=run(['/usr/bin/nm','--defined-only',obj]);assert t['mangled'] in {l.split()[-1] for l in s['stdout'].splitlines() if l.split()};print(t['mangled'])
 elif a.mode=='native':
  import native
  if a.exe:native.PROVIDER=(ROOT/a.exe).resolve()
  assert native.generate()==json.loads((ROOT/TEST/'fixtures.json').read_text());print('Fresh original ARM/provider replay reproduced exact fixtures')
 elif a.mode=='replay':print(json.dumps(replay(exe)))
 else:proof(exe,obj,a.out or pathlib.Path('uc-library/candidates')/NAME/'worker-proof.json',a.integration);print('Fresh proof written')
