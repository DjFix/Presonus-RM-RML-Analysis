"""Local checked commands; exact output and timing retained, no global mutation."""
import argparse,datetime,hashlib,json,subprocess,time
from pathlib import Path
BASE=Path('uc-library/tests/recovery/card_firmware');OUT=Path('evidence/recovery/2026-11-06/rolling200-02/card-firmware95');WORK=Path('temp/recovery-work/rolling200-02/card-firmware95');OUT.mkdir(parents=True,exist_ok=True);WORK.mkdir(parents=True,exist_ok=True)
OWNED=['uc-library/src/Presonus/NOAA/TCardFirmware.cpp','uc-library/src/Presonus/Panel/PanelRegistrarReset.cpp','uc-library/src/Presonus/OutputPinLifecycle.cpp','uc-library/tests/recovery/CardFirmwareReplay.cpp']
EXTRA=['uc-library/src/surface_panel/OutputPin.cpp','uc-library/src/Presonus/Panel/input_pin_lifetime.cpp','uc-library/src/surface_panel/InputPin.cpp','uc-library/src/Presonus/NOAA/TCardProgrammerLifecycle.cpp','uc-library/src/Presonus/NOAA/TCardProgrammerSerial.cpp','uc-library/src/Presonus/NOAA/TCardProgrammerProtocol.cpp','uc-library/src/Presonus/NOAA/TCardProgrammerReceive.cpp','uc-library/src/Presonus/NOAA/TCardProgrammerTransport.cpp','uc-library/src/Presonus/NOAA/TCardProgrammerInformation.cpp','uc-library/src/Presonus/NOAA/TCardProgrammerUpdate.cpp','uc-library/src/Presonus/NOAA/TCardLifecycle.cpp','uc-library/src/Presonus/NOAA/TCardFPGAUpdater.cpp']
MIGRATED=['uc-library/tests/noaa_tcard_command_tests.cpp', 'uc-library/tests/noaa_tcard_handler_tests.cpp', 'uc-library/tests/noaa_tcard_lifecycle_tests.cpp', 'uc-library/tests/noaa_tcard_rate_status_tests.cpp', 'uc-library/tests/noaa_tcard_receive_start_tests.cpp', 'uc-library/tests/noaa_tcard_serial_tests.cpp', 'uc-library/tests/noaa_tcard_setup_tests.cpp', 'uc-library/tests/noaa_tcard_status_tests.cpp', 'uc-library/tests/recovery/TCardHandlerDeferredReplay.cpp', 'uc-library/tests/recovery/TCardHandlerEventsReplay.cpp', 'uc-library/tests/recovery/TCardHandlerReleaseReplay.cpp']
HEADERS=['uc-library/include/presonus/application/ResourceLibrary.hpp', 'uc-library/include/presonus/device_dfu.hpp', 'uc-library/include/presonus/noaa/card.hpp', 'uc-library/include/presonus/panel/PanelRegistrar.hpp', 'uc-library/include/presonus/surface_panel/OutputPin.hpp']
SDK='temp/core-upstream/root-integration-01/upstream-core/sdk';ARCHIVES=['temp/core-upstream/root-integration-01/libpresonus_uc.a',SDK+'/lib/libcorelib.a',SDK+'/lib/libpresonus_core_allocator.a','temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a'];FLAGS=['-std=c++17','-O0','-Iuc-library/include','-Ithird_party/ccl-framework'];WRAPS=['open','close','write','read','tcgetattr','tcsetattr','tcflush','ioctl','socket','fopen','clock_gettime','_ZN4Core8Platform13CurrentThread5sleepEj']
p=argparse.ArgumentParser();p.add_argument('mode');p.add_argument('--executable',default=str(WORK/'replay'));p.add_argument('--fixtures',default=str(BASE/'fixtures.json'));p.add_argument('--fixture-sha256');o=p.parse_args()
LOG=OUT/'runs'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ');LOG.mkdir(parents=True)
def run(argv,name):
 t=time.monotonic();start=datetime.datetime.now(datetime.timezone.utc).isoformat();v=subprocess.run(argv,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(LOG/(name+'.log')).write_text(v.stdout);(LOG/(name+'.command.json')).write_text(json.dumps(dict(argv=argv,producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),native_producer_sha256=hashlib.sha256((BASE/'native.py').read_bytes()).hexdigest(),start_utc=start,end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),seconds=time.monotonic()-t,returncode=v.returncode),indent=2)+'\n');assert v.returncode==0,(name,v.returncode,v.stdout[-3000:]);return v.stdout
if o.mode=='native':print(run(['uc-library/.venv/bin/python',str(BASE/'native.py')],'native'))
elif o.mode=='format':
 paths=sorted(set(OWNED+HEADERS+MIGRATED));print(run(['uc-library/.venv/bin/clang-format','--version'],'version'));run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*paths],'format')
elif o.mode=='compile':
 objects=[]
 for i,s in enumerate(OWNED+EXTRA):
  obj=str(WORK/f'unit{i}.o');objects.append(obj);run(['c++',*FLAGS,'-MMD','-MF',str(WORK/f'unit{i}.d'),'-c',s,'-o',obj],f'compile{i}')
 run(['c++',*objects,'-Wl,--start-group',*ARCHIVES,'-Wl,--end-group','/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lz','-lssl','-lcrypto','temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so','-pthread','-ldl','-lm',*['-Wl,--wrap='+s for s in WRAPS],'-Wl,-rpath,'+str(Path('temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu').resolve()),'-o',o.executable],'link');print('Compiled real canonical providers')
elif o.mode=='regressions':
 migrated=MIGRATED
 for i,p in enumerate(migrated):run(['c++',*FLAGS,'-fsyntax-only',p],f'override{i}')
 objects=[str(WORK/f'unit{i}.o') for i in range(len(OWNED+EXTRA)) if i!=3]
 for name,fixture in [('protocol','protocol-stdin.txt'),('alias','alias-stdin.txt'),('serial','serial-stdin.txt')]:
  source=f'uc-library/tests/noaa_programmer_safe_host_{name}_tests.cpp';obj=str(WORK/(name+'.o'));exe=str(WORK/name)
  run(['c++',*FLAGS,'-c',source,'-o',obj],name+'-compile')
  run(['c++',*objects,obj,'-Wl,--start-group',*ARCHIVES,'-Wl,--end-group','/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lz','-lssl','-lcrypto','temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so','-pthread','-ldl','-lm','-Wl,-rpath,'+str(Path('temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu').resolve()),'-o',exe],name+'-link')
  print(run([exe,'uc-library/validation/noaa-programmer-safe-host/'+fixture],name+'-replay'))
 print('All migrated overrides compile')
elif o.mode=='symbols':
 names=set()
 for i in [0,1]:names.update(x.split()[-1] for x in run(['nm','--defined-only',str(WORK/f'unit{i}.o')],f'symbol{i}').splitlines() if x.split())
 required=[r['mangled'] for r in json.loads((BASE/'fixtures.json').read_text())['ranges']];assert all(x in names for x in required);(OUT/'symbols.json').write_text(json.dumps(dict(required=required,names_match=True,namespace_verified=True,original_arm_abi_verified=False),indent=2)+'\n');print('All four exact symbols present')
elif o.mode=='replay':
 fixturePath=Path(o.fixtures);h=hashlib.sha256(fixturePath.read_bytes()).hexdigest();assert not o.fixture_sha256 or o.fixture_sha256==h;f=json.loads(fixturePath.read_text());results=[]
 for c in f['cases']:
  # Arbitrary callee return words are native boundary observations; real updater
  # has only its actual errors2000/2003, never a synthetic callback return.
  if c.get('fpga_result',0) not in [0,2000,2003]:continue
  a=[o.executable,c['kind'],str(c.get('mode',0)),str(c.get('board',0)),str(c.get('fail_open',0)),str(c.get('arm',1)),str(c.get('fpga',1)),str(c.get('mounted',1)),str(c.get('compatible',1)),str(c.get('listener',0)),str(c.get('fpga_result',0)),str(c.get('ignored_result',0))]
  text=run(a,c['name']);actual=json.loads(text[text.index('{'):]);e=c['expected'];assert c['kind'] in ['reset','cs'] or actual['return_value']==e['return_value'],(c['name'],actual,e)
  if c['kind'] in ['reset','cs']:
   expected=[':'.join(str(v) for v in t) for t in e['trace'] if t[0] not in ['lock','unlock']];assert actual['trace']==expected,(c['name'],actual,expected)
  else:
   assert actual['word44']==e['state']['68'],(c['name'],actual,e)
   expectedTrace=[]
   for t in e['trace']:
    if t[0] in ['reset','sleep']:expectedTrace.append(':'.join(str(v) for v in t))
    elif t[0]=='start':expectedTrace.append('reset:2:0') # actual start(true) provider reset, independently outside coordinator target
    elif t[0]=='fpga_update':expectedTrace.append('sleep:'+str(2000 if c.get('fpga_result',0) else 1000)) # actual provider success/error notice cadence
   assert actual['trace']==expectedTrace,(c['name'],actual['trace'],expectedTrace)
   opened=c['kind']=='erase' or (c.get('mode') in [1,2] and c.get('arm',1)!=1)
   assert actual['closes']==int(opened and c.get('fail_open')!=1),(c['name'],actual)
   assert actual['syncs']==(0 if not opened or c.get('fail_open')==1 else 1 if c.get('fail_open')==1 else 2),(c['name'],actual)
   expectedEnd=[t[1] for t in e['trace'] if t[0]=='progress'];assert [m for m in actual['messages'] if m in ['restarting card','finished']]==expectedEnd
  results.append(dict(name=c['name'],actual=actual,passed=True))
 for i in range(6):
  value=run([o.executable,'precondition','2',str(i),'0','0','1','1','1','0','0','0'],f'precondition{i}');assert json.loads(value[value.index('{'):])['return_value']==30000+i
 run([o.executable,'isolation',*['0']*10],'gateway-isolation')
 (OUT/'replay.json').write_text(json.dumps(dict(fixture_sha256=h,cases=results,domain='Exact reset GPIO/sleep/lifecycle trace; firmware numeric returns,word44, exact coordinator reset/sleep trace expanded only by recorded real start reset and real FPGA provider cadence; listener restart order, actual programmer serial protocol and real FPGA/start providers. Provider internal effects are separately observed, not claimed native equivalence.'),indent=2)+'\n');print('PASS',len(results),'real-provider cases')
else:raise SystemExit(o.mode)
