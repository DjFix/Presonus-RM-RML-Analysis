from pathlib import Path
import subprocess,sys,json,os,re
R=Path.cwd();A=Path(__file__).resolve().parent;W=R/'temp/recovery-work/rolling200-02/card-lifecycle';E=R/'evidence/recovery/2026-11-05/rolling200-02/card-lifecycle';B=R/'temp/core-upstream/root-integration-01';SDK=B/'upstream-core/sdk';W.mkdir(parents=True,exist_ok=True)
mode=sys.argv[1];logs=W/('check-'+mode);logs.mkdir(exist_ok=True);commands=[]
flags=['c++','-std=c++17','-g','-O0','-UNDEBUG','-I'+str(R/'uc-library/include'),'-I'+str(R/'third_party/ccl-framework')]
paths=['uc-library/include/presonus/noaa/card.hpp','uc-library/src/Presonus/NOAA/TCardLifecycle.cpp','uc-library/src/Presonus/NOAA/TCardSerial.cpp','uc-library/tests/noaa_tcard_lifecycle_tests.cpp','uc-library/tests/noaa_tcard_serial_tests.cpp','uc-library/candidates/rolling200-02-card-lifecycle/provider_observe.cpp']
env={**os.environ,'LD_LIBRARY_PATH':str(R/'temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu')}
def run(argv,label):
 p=subprocess.run(list(map(str,argv)),cwd=R,env=env,text=True,capture_output=True);(logs/(label+'.stdout')).write_text(p.stdout);(logs/(label+'.stderr')).write_text(p.stderr);commands.append(dict(argv=list(map(str,argv)),returncode=p.returncode));(logs/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');assert p.returncode==0,(label,p.stderr[-8000:],p.stdout[-1000:]);return p.stdout
if mode=='format':
 print(run([R/'uc-library/.venv/bin/clang-format','--version'],'version'))
 run([R/'uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*paths],'format')
elif mode=='compile':
 for source in paths[1:5]:run([*flags,'-c',R/source,'-o',W/(Path(source).stem+'.o')],Path(source).stem)
 for name in ('TCardSetup','TCardStart','TCardState','TCardReceive','TCardDiagnostics','TCardStatus','TCardResources','TCardCommands','TCardRate'):
  run([*flags,'-c',R/('uc-library/src/Presonus/NOAA/'+name+'.cpp'),'-o',W/(name+'.o')],'dependency-'+name)
 for name,test in [('lifecycle','noaa_tcard_lifecycle_tests'),('serial','noaa_tcard_serial_tests')]:
  wraps=['_Znwm','_ZdlPv','_ZdlPvm','_ZN8Presonus4NOAA8TCardSPI16registerReceiverEPNS0_14ISysexReceiverE','_ZN8Presonus4NOAA8TCardSPI18unRegisterReceiverEPNS0_14ISysexReceiverE'] if name=='lifecycle' else ['_ZN4Core8Platform13CurrentThread5sleepEj','_ZN4Core11DebugPrintfEPKcz','_ZN8presonus4dice19packetClockRawTicksEv','_ZN8Presonus4NOAA13SysexReceiver7waitAckEx']
  run([flags[0],W/(test+'.o'),W/'TCardLifecycle.o',W/'TCardSerial.o',*[W/(n+'.o') for n in ('TCardSetup','TCardStart','TCardState','TCardReceive','TCardDiagnostics','TCardStatus','TCardResources','TCardCommands','TCardRate')],'-Wl,--start-group',B/'libpresonus_uc.a',SDK/'lib/libcorelib.a',SDK/'lib/libpresonus_core_allocator.a',B/'private-glibc29-provider/libpresonus_private_glibc29.a','-Wl,--end-group','/usr/lib/x86_64-linux-gnu/libpng16.so.16','/usr/lib/x86_64-linux-gnu/libz.so.1','-lssl','-lcrypto',R/'temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so','-pthread','-ldl','-lm',*['-Wl,--wrap='+x for x in wraps],'-o',W/name],'link-'+name)
elif mode=='symbols':
 names=''.join(run(['nm','--defined-only',W/n],'symbols-'+n) for n in ('TCardLifecycle.o','TCardSerial.o'))
 for n in range(1,7):
  req=json.loads((R/f'temp/recovery-work/rolling200-02/implementation-plan01/packets-card-lifecycle02/packets/rolling200_02_card_lifecycle_{n:02}/request.json').read_text())
  for t in req['targets']:assert t['mangled'] in names,t['mangled']
 print('six exact original compiler-emitted names present; ELF host needs no decoration')
elif mode in ('replay','replay-lifecycle','replay-serial'):
 for name in (('lifecycle','serial') if mode=='replay' else (mode.removeprefix('replay-'),)):print(run([W/name,E/(name+'-fixtures.txt')],name))
elif mode=='providers':
 source=A/'provider_observe.cpp'
 run([*flags,source,SDK/'lib/libcorelib.a','-pthread','-o',W/'provider-observe'],'compile-provider')
 output=run([W/'provider-observe'],'observe-provider')
 assert output==(E/'provider-observations.txt').read_text()
 print('actual pinned CCL string observations reproduced')
elif mode=='regression':
 for test,fixture in [('noaa_tcard_command_tests','commands'),('noaa_tcard_setup_tests','setup'),('noaa_tcard_status_tests','status'),('noaa_tcard_rate_status_tests','rate-status'),('noaa_tcard_receive_start_tests','receive-start')]:
  source=R/('uc-library/tests/'+test+'.cpp');wraps=sorted(set(re.findall(r'__wrap_(_[A-Za-z0-9_]+)',source.read_text())))
  run([*flags,'-c',source,'-o',W/(test+'.o')],'compile-'+test)
  run([flags[0],W/(test+'.o'),W/'TCardLifecycle.o',W/'TCardSerial.o',*[W/(n+'.o') for n in ('TCardSetup','TCardStart','TCardState','TCardReceive','TCardDiagnostics','TCardStatus','TCardResources','TCardCommands','TCardRate')],'-Wl,--start-group',B/'libpresonus_uc.a',SDK/'lib/libcorelib.a',SDK/'lib/libpresonus_core_allocator.a',B/'private-glibc29-provider/libpresonus_private_glibc29.a','-Wl,--end-group','/usr/lib/x86_64-linux-gnu/libpng16.so.16','/usr/lib/x86_64-linux-gnu/libz.so.1','-lssl','-lcrypto',R/'temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so','-pthread','-ldl','-lm',*['-Wl,--wrap='+x for x in wraps],'-o',W/test],'link-'+test)
  print(run([W/test,R/('uc-library/validation/noaa-tcard-'+fixture+'/stdin.txt')],test))
else:raise SystemExit(mode)
