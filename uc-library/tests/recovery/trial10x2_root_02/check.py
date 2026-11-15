import argparse,pathlib,hashlib,json,subprocess,time,datetime,os
TASK=pathlib.Path(__file__).parent.name;BASE='uc-library/tests/recovery/'+TASK;ROOT=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis');SUP=ROOT/'temp/recovery-work/trial10x2-20261115/root-review/provider-supplement'
H=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--build',action='store_true');p.add_argument('--exe');p.add_argument('--object');p.add_argument('--integration');p.add_argument('--out',required=True);a=p.parse_args();started=time.monotonic();commands=[]
sup=json.load(open(SUP/'PROVIDERS.json'));reg=json.load(open(SUP/'ROOT_REGISTRAR_SOURCES.json'));assert H(SUP/'PROVIDERS.json')=='0e4fc25d3383ae8609932b7e25c4d28bac3ee92b9435c11e8d63b61cd29f0c18';assert H(SUP/'ROOT_REGISTRAR_SOURCES.json')=='9211cc936a68b9331e1c515f9b80953e74353880d726effcb6211bc25eee8bbe'
providers={}
for x in sup['archives'].values(): assert H(x['frozen_read_path'])==x['sha256'];providers[x['frozen_read_path']]=x['sha256']
for x in reg['read_inputs'].values():assert H(x['frozen_read_path'])==x['sha256']
def run(cmd):
 t=time.monotonic();r=subprocess.run(cmd,check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);commands.append(dict(argv=cmd,elapsed_seconds=time.monotonic()-t,output=r.stdout));return r.stdout
work=pathlib.Path('temp/recovery-work/'+TASK);work.mkdir(parents=True,exist_ok=True)
paths=['uc-library/include/presonus/surface_panel/ControlHelpers.hpp','uc-library/src/Presonus/Surface/SurfaceRootComponent.cpp',BASE+'/Replay.cpp']
wrap=['_ZNK4Core8Portable9Component17getParameterByTagEi','_ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE','_ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE','_ZN4Core11DebugPrintfEPKcz','_ZN8Presonus7Surface14PanelRegistrar7runTestENS1_8TestModeEb']
if a.build:
 flags=['c++','-std=c++17','-O0','-g','-ffunction-sections','-fdata-sections','-fno-rtti','-Wno-multichar','-Iuc-library/include','-Ithird_party/ccl-framework']
 run(flags+['-MMD','-MF',str(work/'unit.d'),'-c',paths[1],'-o',str(work/'unit.o')])
 libs=[sup['archives'][x]['frozen_read_path'] for x in ['libpresonus_rm_components.a','libcorelib.a','libpresonus_core_allocator.a','libpresonus_private_glibc29.a']]
 units=[str(work/'unit.o')]
 for i,source in enumerate([BASE+'/Replay.cpp']+[x['frozen_read_path'] for x in reg['read_inputs'].values()]):
  obj=str(work/('provider'+str(i)+'.o'));dep=str(work/('provider'+str(i)+'.d'))
  run(flags+(['-DROOT_UTIL'] if TASK.endswith('02') and i==0 else [])+['-MMD','-MF',dep,'-c',source,'-o',obj]);units.append(obj)
 cmd=flags+units+['-Wl,--gc-sections','-Wl,--start-group']+libs+['-Wl,--end-group','-lpthread','-ldl','-lz','-l:libpng16.so.16','-l:libfreetype.so.6','-lresolv']+['-Wl,--wrap='+s for s in wrap]+['-o',str(work/'replay')]
 run(cmd)
 import shlex
 snapshots=json.load(open(ROOT/'temp/recovery-work/trial10x2-20261115/prepared01/SNAPSHOT.json'))
 captured=json.load(open('temp/recovery-work/trial10x2-20261115/READ_INPUTS-prepared01-trial10x2_root.json'));captured.update(sup['read_inputs']);captured.update(reg['read_inputs'])
 bindings={}
 for dep in work.glob('*.d'):
  for name in shlex.split(dep.read_text().replace('\\\n',' '))[1:]:
   if name in paths or name==BASE+'/Replay.cpp':continue
   if str(ROOT/'temp/recovery-work/trial10x2-20261115/prepared01/snapshot') in name:
    relative=name.split('/snapshot/',1)[1]
   else:relative=name
   if relative not in captured:
    assert relative in snapshots['files'],relative
    frozen=snapshots['references'][relative]['target'];captured[relative]={'sha256':snapshots['files'][relative],'frozen_read_path':frozen}
   binding=captured[relative];assert H(name)==binding['sha256'],name;assert H(binding['frozen_read_path'])==binding['sha256'],relative
   bindings[relative]=binding
 pathlib.Path(a.out).write_text(json.dumps({'commands':commands,'providers':providers,'transitive_bindings':bindings},indent=2)+'\n');print(TASK,'compiled');raise SystemExit
assert a.exe and a.object and a.integration
run(['uc-library/.venv/bin/python',BASE+'/native.py','--verify'])
run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*paths])
req=json.load(open('temp/recovery-work/trial10x2-20261115/prepared01/packets/'+TASK+'/request.json'));symbols=run(['nm',a.object]);assert req['targets'][0]['mangled'] in symbols
fixture=json.load(open(BASE+'/fixtures.json'));observations=[]
provider=run([str(pathlib.Path(a.exe).resolve()),'--observe-provider']);assert 'PROVIDER 2 1 1 0 1' in provider
for case in fixture['cases']:
 output=run([str(pathlib.Path(a.exe).resolve()),*map(str,case['args'])]);rows=[]
 for line in output.splitlines():
  if line.startswith('ROW '):
   state,trace=line[4:].split('|');rows.append(dict(state=list(map(int,state.split())),calls=[x for x in trace.split(',') if x]))
 assert len(rows)==len(case['rows']),(case,rows,output)
 for got,expected in zip(rows,case['rows']):
  assert got['state']==expected['state'],(case,got,expected)
  if not got['state'][-1]:assert got['calls']==expected['calls'],(case,got,expected)
 observations.append(dict(args=case['args'],rows=rows,stdout=output))
sourcepaths=paths+[BASE+'/native.py',BASE+'/check.py',BASE+'/fixtures.json'];sources={x.removeprefix('uc-library/'):H(x) for x in sourcepaths}
providerpaths=['third_party/ccl-framework/core/portable/corecomponent.h','third_party/ccl-framework/core/portable/corecomponent.cpp','third_party/ccl-framework/core/portable/coreparams.h','third_party/ccl-framework/core/portable/coreparams.cpp','third_party/ccl-framework/core/public/corevector.h','third_party/ccl-framework/core/system/coredebug.h','third_party/ccl-framework/core/system/coredebug.cpp']
# Readiness schema reserves repository_sources exclusively for pinned Core.
# Actual application providers keep their exact current hashes in uc-library sources.
build=json.load(open(work/'build.json' if a.integration=='local' else pathlib.Path('uc-library/candidates')/TASK/'worker-proof.json'))
transitive=build.get('transitive_bindings',build.get('transitive_source_bindings',{}))
repo_sources={x:H(x) for x in providerpaths}
for name,digest in {**{x:d['sha256'] for x,d in reg['read_inputs'].items()},**{x:d['sha256'] for x,d in transitive.items()}}.items():
 if name.startswith('uc-library/'):
  assert H(name)==digest,name
  sources[name.removeprefix('uc-library/')]=digest
 elif name.startswith('third_party/ccl-framework/core/'):
  assert H(name)==digest,name
  repo_sources[name]=digest
 else:raise AssertionError('Unclassified proof dependency '+name)

domain=('Actual original 104-byte ARM application body: touchscreen flag 0/1, registrar null/non-null, 0/1/2 duplicate observers, screen/tag38/tag903 mandatory-port failure; actual CCL first-occurrence removal and actual runTest111(false) timer/flag cleanup.' if TASK.endswith('01') else 'Actual original 156-byte ARM application body: first enable, repeated enable, last disable, intermediate disable, repeated underflow reset/debug/remove, two root instances sharing process counter with distinct observers/parameters; real empty/missing screen error adaptation.')
limitations=['Original return declaration unresolved; portable void is intentional.','Original member declarations, inheritance, layouts, ARM ABI and hardware unproved.','Native executes original application instructions only; CCL calls and getMainScreen/registrar are explicit boundary models. Actual CCL sources and registrar provider execute independently in portable replay.','Mandatory missing ports are portable logic_error adaptations of invalid native provider use; error traces are not asserted identical.','Counter overflow implementation is explicit wrapping but extreme counts are not behaviorally exercised; concurrent/reentrant mutation excluded.']
records=[dict(original_elf_sha256=x['original_elf_sha256'],mangled=x['mangled'],original_address=x['address'],sources=sources,repository_sources=repo_sources,domain=domain,portable_ready=False,declaration_uncertainties=limitations[:2],cpp_compiled=True,mangling_namespace_checked=True,original_function_verified=False,hardware_verified=False) for x in req['targets']]
proof=dict(transitive_source_bindings=build.get('transitive_bindings',build.get('transitive_source_bindings',{})),build_commands=build.get('commands') if a.integration=='local' else build['build_commands'],version=1,task_id=TASK,phase='local' if a.integration=='local' else 'canonical',session_id=os.getenv('CODEX_THREAD_ID'),utc_end=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-started,sources=sources,repository_sources=repo_sources,domain=domain,cpp_differential_passed=True,compiled_original_mangled_names_matched=True,mangling_namespace_checked=True,functions=[dict(x,cpp_differential_passed=True,range_verified=True,native_cases=len(fixture['cases'])) for x in records],fixture={'path':BASE+'/fixtures.json','sha256':H(BASE+'/fixtures.json')},producer_sha256=H(__file__),oracle_producer_sha256=H(BASE+'/native.py'),native_range={k:v for k,v in fixture.items() if k not in ['cases']},executable={'path':a.exe,'sha256':H(a.exe)},objects={a.object:H(a.object)},format={'version':run(['uc-library/.venv/bin/clang-format','--version']).strip(),'sources':{x:H(x) for x in paths}},archives=providers,provider_observations=provider,provider_supplement={'path':str(SUP/'PROVIDERS.json'),'sha256':H(SUP/'PROVIDERS.json'),'registrar_sources':str(SUP/'ROOT_REGISTRAR_SOURCES.json'),'registrar_sha256':H(SUP/'ROOT_REGISTRAR_SOURCES.json')},proposed_readiness={'canonical_binding_pending':True,'ready':[],'pending':records},limitations=limitations,commands=commands,observations=observations)
if a.integration!='local':proof['integration']={'path':a.integration,'sha256':H(a.integration)}
pathlib.Path(a.out).write_text(json.dumps(proof,indent=2)+'\n');print(TASK,'passed',len(fixture['cases']),'native/provider/product cases')
