from pathlib import Path
import hashlib,json,os,shlex,subprocess,sys,time,datetime
R=Path.cwd();A=Path('uc-library/candidates/rolling200_02_rack_lifecycle');W=Path('temp/recovery-work/rack-lifecycle-local');EBASE=Path('evidence/recovery/2026-11-05/rolling200-02/rack-lifecycle08');mode=sys.argv[1];E=EBASE/'runs'/(mode+'-'+str(time.time_ns()));B=Path('temp/core-upstream/root-integration-01');SDK=B/'upstream-core/sdk'
W.mkdir(parents=True,exist_ok=True);E.mkdir(parents=True,exist_ok=True)
commands=[]
(W/('last-'+mode+'.json')).write_text(json.dumps({'logs':str(E)})+'\n')
CPP=['uc-library/src/Presonus/Panel/'+n+'.cpp' for n in ['RackPanelComponent','PanelComponentLifecycle','PanelComponent','PanelComponentTests','FrontPanelLifecycle','FrontPanelComponent','FrontPanelRouting','FrontPanelUartTest','PanelRegistrar']]
SOURCES=CPP[:2]+['uc-library/src/Presonus/Panel/FrontPanelLifecycle.cpp']+['uc-library/include/presonus/panel/RackPanelComponent.hpp','uc-library/include/presonus/panel/PanelComponent.hpp','uc-library/tests/recovery/RackPanelLifecycleReplay.cpp','uc-library/tests/recovery/PanelOwnerRegression.cpp']
FLAGS=['c++','-std=c++17','-fno-rtti','-g','-O0','-UNDEBUG','-Wno-multichar','-DCORE_PLATFORM_LINUX=1','-Iuc-library/include','-Ithird_party/ccl-framework']
LINK=['-Wl,--start-group',str(B/'libpresonus_uc.a'),str(SDK/'lib/libcorelib.a'),str(SDK/'lib/libpresonus_core_allocator.a'),str(B/'private-glibc29-provider/libpresonus_private_glibc29.a'),'-Wl,--end-group','-pthread','-ldl','-lz','-lssl','-lcrypto','/usr/lib/x86_64-linux-gnu/libpng16.so.16',str(Path('temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so'))]
env={**os.environ,'TMPDIR':str(W.resolve()),'LD_LIBRARY_PATH':str(R/'temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu')}
def run(argv,label,input=None):
 argv=list(map(str,argv));started=datetime.datetime.now(datetime.timezone.utc).isoformat();before=time.monotonic();p=subprocess.run(argv,input=input,capture_output=True,text=True,env=env);(E/(mode+'-'+label+'.stdout')).write_text(p.stdout);(E/(mode+'-'+label+'.stderr')).write_text(p.stderr);commands.append(dict(argv=argv,returncode=p.returncode,start_utc=started,seconds=time.monotonic()-before));(E/(mode+'-commands.json')).write_text(json.dumps(commands,indent=2)+'\n');assert p.returncode==0,(label,p.stderr[-6000:],p.stdout[-1000:]);return p.stdout
if mode=='format':
 print(run(['uc-library/.venv/bin/clang-format','--version'],'version'));run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*SOURCES],'check')
elif mode=='compile':
 for source in CPP:run([*FLAGS,'-c',source,'-o',W/(Path(source).stem+'.o')],Path(source).stem)
 objects=[W/(Path(s).stem+'.o') for s in CPP]
 for test in ['RackPanelLifecycleReplay','PanelOwnerRegression']:
  wraps=['-Wl,--wrap=_ZN8Presonus10DelayTimerD1Ev','-Wl,--wrap=_ZN8Presonus5Panel14PanelComponentD2Ev'] if test=='RackPanelLifecycleReplay' else []
  run([*FLAGS,'uc-library/tests/recovery/'+test+'.cpp',*objects,*LINK,*wraps,'-o',W/test],'link-'+test)
 for test in ['graph_trial07_frontpanel_tests','graph_trial07_rackpanel_tests']:
  run([*FLAGS,'uc-library/tests/'+test+'.cpp',*objects,*LINK,'-o',W/test],'link-'+test)
 print('PASS affected production compile and four executable links')
elif mode=='symbols':
 output=run(['nm','--defined-only',W/'RackPanelComponent.o'],'nm');names={line.split()[-1] for line in output.splitlines() if len(line.split())>=3}
 for r in json.loads((A/'fixtures.json').read_text())['ranges']:assert r['mangled'] in names,r
 print('PASS all five exact compiler-emitted Rack original symbols; host ELF needs no decoration')
elif mode=='replay':
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('--executable',default=str(W/'RackPanelLifecycleReplay'));parser.add_argument('--owners',default=str(W/'PanelOwnerRegression'));parser.add_argument('--fixtures',default=str(A/'fixtures.json'));options=parser.parse_args(sys.argv[2:])
 original=json.loads(run(['uc-library/.venv/bin/python',A/'native.py'],'native'));fixture=json.loads(Path(options.fixtures).read_text());assert original==fixture
 binary=options.executable
 lines=[]
 for p in fixture['parameters']:
  lines.append(' '.join([str(p['type']),str(p['tag']),json.dumps(p['name']),json.dumps(p['title']),*[str(x) for x in p['values']],str(p['flags']),*[json.dumps(s) for s in p['strings']]]))
 expected=run([binary,'provider'],'provider',input='\n'.join(lines)+'\n')
 for variant in ['c1','c2']:assert run([binary,variant],variant)==expected
 for case in fixture['cases']:
  if case['task']<16:continue
  variant={16:'d0',17:'d1',18:'d2'}[case['task']];trace=[]
  for call in case['trace']:
   if call[0]=='timer_dtor':trace.append(10+([0x150,0x170,0x190,0x1b0].index(call[1])))
   elif call[0]=='vector_dtor' and case['filled']:trace.append([0xf4,0x108,0x11c,0x130].index(call[1]))
   elif call[0]=='base_dtor':trace.append(20)
   elif call[0]=='object_delete':trace.append(4)
  actual=list(map(int,run([binary,variant,int(case['filled'])],variant+str(case['filled'])).split()));assert actual==trace,(case,actual,trace)
 print(run([options.owners],'owners'))
 print('PASS eight independent native body executions, two original constructor variants, six original destructor/container states and exact provider metadata')
elif mode=='regression':
 for name,fixture in [('frontpanel','native-fixtures.json'),('rackpanel','fixtures.json')]:
  base=Path('uc-library/tests/recovery/trial07')/name
  print(run(['uc-library/.venv/bin/python',base/'replay.py','--executable',W/('graph_trial07_'+name+'_tests'),'--fixtures',base/fixture],name))
else:raise SystemExit(mode)
