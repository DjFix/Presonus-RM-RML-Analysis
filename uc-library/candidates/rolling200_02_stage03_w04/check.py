from pathlib import Path
import subprocess,json,shlex,sys,hashlib,os
R=Path.cwd();A=Path(__file__).resolve().parent;W=R/'temp/recovery-work/rolling200-02/stage03-w04';E=R/'evidence/recovery/2026-11-05/rolling200-02/stage03-w04';B=R/'temp/core-upstream/root-integration-01';SDK=B/'upstream-core/sdk';W.mkdir(exist_ok=True,parents=True);E.mkdir(exist_ok=True,parents=True)
mode=sys.argv[1];E=W/('check-'+mode);E.mkdir(exist_ok=True)
source=R/'uc-library/src/Presonus/VUMeterControl.cpp';rows=json.loads((B/'compile_commands.json').read_text());row=next(x for x in rows if x['file']==str(source));flags=shlex.split(row['command']);flags=flags[:flags.index('-o')];flags=[x for x in flags if x not in ['-DNDEBUG','-DNDEBUG=1']];flags+=['-UNDEBUG'];obj=W/'VUMeterControl.o';exe=W/'replay';env={**os.environ,'LD_LIBRARY_PATH':str(R/'temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu')};commands=[]
def run(argv,label):
 p=subprocess.run(list(map(str,argv)),cwd=R,env=env,text=True,capture_output=True);(E/(label+'.stdout')).write_text(p.stdout);(E/(label+'.stderr')).write_text(p.stderr);commands.append(dict(argv=list(map(str,argv)),returncode=p.returncode));(E/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');assert p.returncode==0,(label,p.stderr[-6000:]);return p.stdout
if mode=='compile':
 run([*flags,'-c',source,'-o',obj],'compile-source');run([*flags,'-c',A/'replay.cpp','-o',W/'replay.o'],'compile-replay')
 run([flags[0],obj,W/'replay.o',B/'libpresonus_uc.a',SDK/'lib/libcorelib.a',SDK/'lib/libpresonus_core_allocator.a',B/'private-glibc29-provider/libpresonus_private_glibc29.a','/usr/lib/x86_64-linux-gnu/libpng16.so.16','/usr/lib/x86_64-linux-gnu/libz.so.1','-lssl','-lcrypto',R/'temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so','-pthread','-ldl','-lm','-Wl,--wrap=_ZN8presonus4dice19packetClockRawTicksEv','-Wl,--wrap=_ZN4Core8Portable14ViewAttributes9getBitmapERKNS0_10AttributesEPKc','-Wl,-Map,'+str(W/'replay.map'),'-o',exe],'link')
elif mode=='symbols':
 names=run(['nm','--defined-only',obj],'symbols');want=['_ZN8Presonus14VUMeterControl13setAttributesERKN4Core8Portable10AttributesE','_ZN8Presonus14VUMeterControl6onIdleEv'];assert all(x in names for x in want)
elif mode=='replay':print(run([exe],'replay'))
else:raise SystemExit(mode)
