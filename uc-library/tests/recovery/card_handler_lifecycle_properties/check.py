"""Read-only checks and reproducible isolated Handler build/replay."""
import argparse,datetime,hashlib,json,re,subprocess,time
from pathlib import Path
BASE=Path('uc-library/tests/recovery/card_handler_lifecycle_properties');WORK=Path('temp/recovery-work/rolling200-02/handler132-nortti265');OUT=Path('evidence/recovery/2026-11-06/rolling200-02/handler132-nortti265')
SOURCES=['uc-library/src/Presonus/NOAA/TCardHandlerLifecycle.cpp','uc-library/src/Presonus/NOAA/TCardHandlerProperties.cpp','uc-library/src/Presonus/NOAA/TCardHandlerEventQueue.cpp','uc-library/src/Presonus/NOAA/TCardHandlerEvents.cpp','uc-library/src/Presonus/NOAA/TCardHandlerRelease.cpp','uc-library/tests/recovery/CardHandlerLifecyclePropertiesReplay.cpp']
HEADERS=['uc-library/include/presonus/noaa/card_handler.hpp','uc-library/include/presonus/noaa/card_handler_events.hpp','uc-library/include/presonus/noaa/card_handler_state.hpp']
SDK='temp/core-upstream/root-integration-01/upstream-core/sdk';ARCHIVES=['temp/core-upstream/root-integration-01/libpresonus_uc.a',SDK+'/lib/libcorelib.a',SDK+'/lib/libpresonus_core_allocator.a','temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a']
FLAGS=['-std=gnu++20','-UNDEBUG','-fno-lto','-Ulinux','-O0','-g','-fno-rtti','-Wno-multichar','-pthread','-Iuc-library/include','-Ithird_party/ccl-framework']
PRODUCTION_FLAGS=['-std=gnu++20','-O3','-DNDEBUG','-Ulinux','-fno-rtti','-g','-Iuc-library/include','-Ithird_party/ccl-framework']
p=argparse.ArgumentParser();p.add_argument('mode');p.add_argument('--executable',default=str(WORK/'noaa_tcard_handler_lifecycle_properties_replay'));p.add_argument('--fixtures',default=str(BASE/'fixtures.json'));p.add_argument('--fixture-sha256');o=p.parse_args();WORK.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
LOG=OUT/'runs'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ');LOG.mkdir(parents=True)
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(argv,name):
 inputs={str(p):digest(p) for p in [*SOURCES,*HEADERS,BASE/'native.py',BASE/'fixtures.json',BASE/'check.py']};start=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic();v=subprocess.run(argv,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180);(LOG/(name+'.log')).write_text(v.stdout);(LOG/(name+'.command.json')).write_text(json.dumps(dict(argv=argv,input_sha256=inputs,producer_sha256=digest(__file__),start_utc=start,end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),seconds=time.monotonic()-t,returncode=v.returncode),indent=2)+'\n');assert v.returncode==0,(name,v.returncode,v.stdout[-5000:]);assert all(digest(p)==h for p,h in inputs.items()),'Bound inputs changed during command';return v.stdout
wraps=sorted(set(re.findall(r'__wrap_([a-zA-Z0-9_]+)\(',Path(SOURCES[-1]).read_text())))
# clang-format separates C++ function names and '(' by whitespace only if needed.
wraps=sorted(set(wraps+re.findall(r'__wrap_([a-zA-Z0-9_]+)\s*\(',Path(SOURCES[-1]).read_text())))
link=['-Wl,--start-group',*ARCHIVES,'-Wl,--end-group','/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lz','-lssl','-lcrypto','temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so','-pthread','-ldl','-lm','-Wl,-rpath,'+str(Path('temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu').resolve())]
if o.mode=='native':print(run(['uc-library/.venv/bin/python',str(BASE/'native.py'),'--verify'],'native'))
elif o.mode=='format':
 print(run(['uc-library/.venv/bin/clang-format','--version'],'version'));run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*SOURCES,*HEADERS],'format')
elif o.mode=='compile':
 objs=[]
 for i,s in enumerate(SOURCES):
  obj=str(WORK/f'unit{i}.o');objs.append(obj);run(['c++',*(PRODUCTION_FLAGS if i<len(SOURCES)-1 else FLAGS),'-MMD','-MF',str(WORK/f'unit{i}.d'),'-c',s,'-o',obj],f'compile{i}')
 run(['c++',*objs,*link,*['-Wl,--wrap='+s for s in wraps],'-o',o.executable],'link');print('PASS actual integrated Card/Router/CCL Handler replay compiled')
elif o.mode=='symbols':
 names=set()
 for i in [0,1]:names.update(x.split()[-1] for x in run(['nm','--defined-only',str(WORK/f'unit{i}.o')],f'symbol{i}').splitlines() if x.split())
 required=[r['mangled'] for r in json.loads(Path(o.fixtures).read_text())['ranges']];assert all(n in names for n in required)
 (OUT/'symbols.json').write_text(json.dumps(dict(required=required,names_match=True,namespace_verified=True,original_arm_abi_verified=False),indent=2)+'\n');print('PASS six exact original names')
elif o.mode=='replay':
 f=json.loads(Path(o.fixtures).read_text());assert not o.fixture_sha256 or digest(o.fixtures)==o.fixture_sha256;results=[]
 boolparams={'setAvbTapeRxToDigitalReturnRoute':[2],'setDspToAvbTxRoute':[4],'setAvbToSlaveFwRecordRoute':[3],'setAvbToDacBypassRoute':[4],'setMixerInputRoute':[2]}
 for i,c in enumerate(f['cases']):
  if c['kind']!='property' or c['id']==123:continue
  a=[o.executable,'property',str(c['id']),str(c['mode']),str(c['size']),*[str(x) for x in c['words']],'0'];s=run(a,f'property{i}');actual=json.loads(s[s.index('{'):]);expected=[]
  for t in c['expected']['trace']:
   if t[0] in ['queue.lock','queue.unlock']:continue
   values=t[1:]
   for j in boolparams.get(t[0],[]):values[j]=int(values[j]!=0)
   if t[0]=='setGEQTDMSlotInsert':values=[v&0xffffffff for v in values]
   expected.append(':'.join(map(str,[t[0],*values])))
  assert actual['trace']==expected,(i,c,actual,expected)
  results.append(dict(case=i,passed=True,actual=actual))
 for ident in sorted({c['id'] for c in f['cases'] if c['kind']=='property'}-{123,0x73657269,0x65666972,0x666c6576,0x75647461,0x73637270,0x73657475}):
  s=run([o.executable,'property',str(ident),'1','7','1','2','3','4','1','0'],f'undersized{ident}');a=json.loads(s[s.index('{'):]);assert a['trace']==['exception'],(ident,a)
 for ident in [0x73657269,0x65666972,0x666c6576,0x75647461,0x73637270]:
  s=run([o.executable,'property',str(ident),'1','28','1','2','3','4','1','1'],f'exception{ident}');a=json.loads(s[s.index('{'):]);expected=['main.lock','purge','main.unlock','exception'] if ident in [0x73657269,0x65666972,0x666c6576] else ['purge','exception'];assert a['trace']==expected,(ident,a)
 for c in f['cases']:
  if c['kind']!='property' or c['id']!=123 or c.get('nonempty'):continue
  text=run([o.executable,'enqueue',str(c['size']),c['expected']['copied'],str(c['starve'])],f"enqueue{c['size']}-{c['starve']}");a=json.loads(text[text.index('{'):]);expected=[':'.join(map(str,t)) for t in c['expected']['trace'] if t[0] in ['queue.lock','queue.unlock','sleep']];assert a['trace']==expected,(c,a,expected)
 for n in [8,16,17,32,33,512]:
  native=next(c for c in f['cases'] if c['kind']=='property' and c['id']==123 and c['size']==n and c.get('starve')==2)
  assert [t for t in native['expected']['trace'] if t[0]=='sleep']==[['sleep',4],['sleep',4]]
  run([o.executable,'queue',str(n),native['expected']['copied']],f'queue{n}')
 for c in f['cases']:
  if c['kind']=='property' and c.get('nonempty'):assert c['expected']['retained_fifo_head'] and sum(c['expected']['pool_counts'])==1
 run([o.executable,'fifo'],'mixed-fifo')
 lifecycles=[]
 for ctor in ['C1','C2']:
  for dtor in ['D0','D1','D2']:
   for equal in [0,1]:
    s=run([o.executable,'lifecycle',ctor,dtor,str(equal)],f'lifecycle{ctor}{dtor}{equal}');a=json.loads(s[s.index('{'):]);projected=[]
    for t in a['trace']:
     if t in ['register.card','register.router','unregister.card','unregister.router']:continue
     projected.append({'register.handler':'register','unregister.handler':'unregister','delete.card':'card.D0'}.get(t,t))
    native=[]
    for kind in [ctor,dtor]:
     c=next(c for c in f['cases'] if c['kind']==kind and not c.get('fail') and not c['spi_absent'] and c['singleton_equal']==bool(equal))
     for t in c['expected']['trace']:
      if t[0] in ['card.ctor','router.ctor','register','priority','unregister','card.D0','router.D1']:native.append(':'.join(map(str,t)))
      elif t[0]=='delete':native.append('.'.join(t))
     if kind.startswith('D'):assert c['expected']['handler_deallocated']==(kind=='D0') and c['expected']['card_deallocated']
    assert projected==native,(ctor,dtor,equal,a,projected,native)
    lifecycles.append(a)
 failureResults=[]
 for c in f['cases']:
  if not c.get('fail'):continue
  text=run([o.executable,'ctor-failure',c['fail'],c['kind'],str(int(c['singleton_equal']))],f"failure-{c['kind']}-{c['fail']}-{c['singleton_equal']}");actual=json.loads(text[text.index('{'):]);projected=[]
  for t in actual['trace']:
   if t in ['register.card','register.router']:continue
   projected.append({'register.handler':'register'}.get(t,t))
  expected=[]
  for t in c['expected']['trace']:
   if t[0] in ['card.ctor','router.ctor','register']:expected.append(t[0])
   elif t[0]=='delete':expected.append('.'.join(t))
  assert projected==expected and actual['retained']==len(c['expected']['retained_dependencies']),(c,actual,expected)
  failureResults.append(actual)
 a=lifecycles
 (OUT/'replay.json').write_text(json.dumps(dict(fixture_sha256=digest(o.fixtures),cases=results,queue_case_count=60,exception_case_count=5,constructor_failure_cases=failureResults,lifecycle=a,domain='All27 original immediate dispatcher IDs, native mode guards/argument reads/call order, actual provider calls behind observing forwarding wrappers. Real Card firmware offline fail-open result2008/unchanged update0. Six pool boundaries with starvation/stop/allocation recovery. Default real owned lifetime and actual deleting destructor deallocation.'),indent=2)+'\n');print('PASS',len(results),'immediate native/provider comparisons;65 queue/exception cases;owned lifecycle')
elif o.mode=='ctest':
 directory=WORK/'ctest';directory.mkdir(parents=True,exist_ok=True)
 name='noaa_tcard_handler_lifecycle_properties_replay'
 argv=[str(Path('uc-library/.venv/bin/python').absolute()),str((BASE/'check.py').absolute()),'replay','--executable',str(Path(o.executable).absolute()),'--fixtures',str(BASE/'fixtures.json'),'--fixture-sha256',digest(BASE/'fixtures.json')]
 quote=lambda s:'"'+s.replace('\\','/').replace('"','\\"')+'"'
 (directory/'CTestTestfile.cmake').write_text('add_test('+name+' '+ ' '.join(map(quote,argv))+')\nset_tests_properties('+name+' PROPERTIES WORKING_DIRECTORY '+quote(str(Path.cwd()))+' TIMEOUT 180)\n')
 print(run(['uc-library/.venv/bin/ctest','--test-dir',str(directory),'--output-on-failure','-R','^'+name+'$'],'canonical-ctest'))
elif o.mode=='regressions':
 specs=[
 ('handler',['uc-library/tests/noaa_tcard_handler_tests.cpp'],[['uc-library/validation/noaa-tcard-handler/stdin.txt']]),
 ('deferred',['uc-library/tests/recovery/TCardHandlerDeferredReplay.cpp'],[['uc-library/candidates/rolling200_02_handler_deferred_01/stdin.txt']]),
 ('events',['uc-library/tests/recovery/TCardHandlerEventsReplay.cpp'],[['uc-library/candidates/rolling200_02_handler_runtime08_01/stdin.txt',case] for case in ['stopped','deadlines','fifo-pools','cadence','signed-wide']]),
 ('card-lifecycle',['uc-library/tests/noaa_tcard_lifecycle_tests.cpp'],[['evidence/recovery/2026-11-05/rolling200-02/card-lifecycle/lifecycle-fixtures.txt']]),
 ('card-serial',['uc-library/tests/noaa_tcard_serial_tests.cpp'],[['evidence/recovery/2026-11-05/rolling200-02/card-lifecycle/serial-fixtures.txt']]),
 ('router-lifecycle',['uc-library/tests/noaa_router_lifecycle_tests.cpp','uc-library/tests/noaa_router_lifecycle_core_scope.cpp'],[['uc-library/validation/noaa-router-remaining/lifecycle-stdin.txt']])]
 specs.append(('release',['uc-library/tests/recovery/TCardHandlerReleaseReplay.cpp'],[]))
 for name,sources,cases in specs:
  objs=[];regwrap=set()
  for i,source in enumerate(sources):
   obj=str(WORK/f'reg-{name}-{i}.o');objs.append(obj)
   run(['c++',*FLAGS,*(['-frtti'] if name in ['card-lifecycle','router-lifecycle'] else []),'-fno-devirtualize','-fno-devirtualize-speculatively','-c',source,'-o',obj],f'{name}-compile{i}')
   regwrap.update(re.findall(r'__wrap_([a-zA-Z0-9_]+)\s*\(',Path(source).read_text()))
  exe=str(WORK/f'reg-{name}')
  run(['c++',*([str(WORK/f'unit{i}.o') for i in range(5)] if name in ['handler','deferred','events','release'] else []),*objs,*link,*['-Wl,--wrap='+w for w in sorted(regwrap)],'-o',exe],name+'-link')
  if name=='release':run(['uc-library/.venv/bin/python','evidence/recovery/2026-11-05/rolling200-02/handler-release/replay.py','replay','--binary',exe],name+'-replay')
  for i,args in enumerate(cases):
   run([exe,*args],f'{name}-replay{i}');print('PASS regression',name,i)
 print('PASS executable existing Handler/Card/Router consumers')

else:raise SystemExit(o.mode)
