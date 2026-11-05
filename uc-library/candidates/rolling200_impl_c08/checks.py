import pathlib,json,subprocess,sys,hashlib,datetime,os
ROOT=pathlib.Path.cwd();OWN=pathlib.Path('uc-library/candidates/rolling200_impl_c08');WORK=pathlib.Path('temp/recovery-work/rolling200_impl_c08');OUT=pathlib.Path('evidence/recovery/2026-11-05/rolling200-implementation01/rolling200_impl_c08');FIX=OUT/'native-fixture.json'
SRC=pathlib.Path('uc-library/src/Presonus/Dsp/ControllerInfo.cpp');HDR=pathlib.Path('uc-library/include/presonus/dsp/ControllerInfo.hpp');BASE=pathlib.Path('uc-library/include/presonus/dsp/Controller.hpp');EXE=WORK/'replay';OBJ=WORK/'ControllerInfo.o';F='uc-library/.venv/bin/clang-format';sdk='temp/core-upstream/root-integration-01/upstream-core/sdk'
flags=['g++','-std=c++20','-O2','-UNDEBUG','-Ulinux','-DCORE_USE_OPENSSL=1','-Iuc-library/include','-isystem',sdk+'/include/presonus-core-5']
LOG=WORK/'check-logs';LOG.mkdir(parents=True,exist_ok=True)
commands=[]
def run(label,argv):
 start=datetime.datetime.now(datetime.timezone.utc).isoformat();r=subprocess.run(list(map(str,argv)),capture_output=True,text=True);(LOG/(label+'.stdout')).write_text(r.stdout);(LOG/(label+'.stderr')).write_text(r.stderr);commands.append(dict(label=label,argv=list(map(str,argv)),returncode=r.returncode,start=start,end=datetime.datetime.now(datetime.timezone.utc).isoformat()));assert r.returncode==0,(label,r.stderr[-4000:]);return r.stdout
mode=sys.argv[1]
if len(sys.argv)>2: EXE=pathlib.Path(sys.argv[2])
if len(sys.argv)>3: FIX=pathlib.Path(sys.argv[3])
if mode=='format':
 print(run('formatter-version',[F,'--version']));run('format',[F,'--style=file','--fallback-style=LLVM','--dry-run','--Werror',SRC,HDR,BASE,OWN/'driver.cpp'])
elif mode=='compile':
 run('compile',[*flags,'-c',SRC,'-o',OBJ]);run('base-compile',[*flags,'-c','uc-library/src/Presonus/Dsp/Controller.cpp','-o',WORK/'Controller.o']);run('link',[*flags,OWN/'driver.cpp',OBJ,WORK/'Controller.o','temp/core-upstream/root-integration-01/libpresonus_uc.a',sdk+'/lib/libcorelib.a','temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a','-pthread','-ldl','-lm','-o',EXE])
elif mode=='symbols':
 nm=run('symbols',['nm','--defined-only',OBJ]);names={x.split()[-1] for x in nm.splitlines() if x.split()}
 for i in range(1,5):
  req=json.load(open(f'temp/recovery-work/rolling200-implementation01/packets-batch04/packets/rolling200_impl_c08_{i:02}/request.json'));assert all(x['mangled'] in names for x in req['targets'])
elif mode=='replay':
 cases=json.load(open(FIX))['cases'];p=WORK/'cases.txt';p.write_text('\n'.join(' '.join(map(str,[c['kind'],c['mode'],c.get('formatter',0),c.get('value',0),c.get('capacity',0),int(c.get('integer',0)),int(c.get('range',0)),json.dumps(c.get('input','')),int(c.get('success',0)),c.get('flags',0),c.get('size',0),int(c.get('match',0)),c.get('index',0)])) for c in cases)+'\n');result=run('replay',[EXE,p]);actual=[json.loads(x) for x in result.splitlines()];assert len(actual)==len(cases)
 for i,(c,a) in enumerate(zip(cases,actual)):
  for k in ['return','output','output_hex']:
   if k in c:assert a[k]==c[k],(i,k,c,a)
  traces=[t for t in c['trace'] if t[0]=='formatter'];assert a['formatter']==(traces[0] if traces else None),(i,'formatter',c,a)
 print(json.dumps(dict(passed=True,cases=len(cases),original_execution='native-fixture.json',provider='actual pinned IntFormatter print/scan; boundary Data observed separately')))
else:raise ValueError(mode)
(LOG/(mode+'-checks.json')).write_text(json.dumps(commands,indent=2)+'\n')
