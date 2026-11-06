"""Reviewable local checks; no shared integration/registry changes."""
import argparse, datetime, hashlib, json, platform, subprocess, sys, time
from pathlib import Path
BASE=Path('uc-library/tests/recovery/fpga_programming');OUT=Path('evidence/recovery/2026-11-05/rolling200-02/fpga-resume18');WORK=Path('temp/recovery-work/rolling200-02/fpga-resume18');OUT.mkdir(parents=True,exist_ok=True);WORK.mkdir(parents=True,exist_ok=True)
SOURCES=['uc-library/src/Presonus/NOAA/TCardFPGAUpdater.cpp','uc-library/src/application/FirmwareBundleStreams.cpp','uc-library/src/Presonus/NOAA/SysexReceiver.cpp','uc-library/src/Presonus/NOAA/SysexReceiverWait.cpp','uc-library/src/Presonus/NOAA/SysexPacketConstruction.cpp','uc-library/src/Presonus/NOAA/TCardSPIPackets.cpp','uc-library/src/Presonus/NOAA/TCardSPIService.cpp','uc-library/src/Presonus/DICE/Codec.cpp','uc-library/src/portable/dice/ResponseWait.cpp','uc-library/tests/recovery/TCardFPGAProgrammingReplay.cpp']
FORMAT=[SOURCES[0],SOURCES[-1],'uc-library/include/presonus/noaa/TCardFPGAUpdater.hpp']
SDK='temp/core-upstream/root-integration-01/upstream-core/sdk';ARCHIVES=['temp/core-upstream/root-integration-01/libpresonus_uc.a',SDK+'/lib/libcorelib.a',SDK+'/lib/libpresonus_core_allocator.a'];LINKS=ARCHIVES+['/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lz','-lssl','-lcrypto','temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so','-pthread','-ldl','-lm','-Wl,-rpath,'+str(Path('temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu').resolve())]
FLAGS=['-std=c++17','-O2','-Iuc-library/include','-Ithird_party/ccl-framework']
parser=argparse.ArgumentParser();parser.add_argument('mode');parser.add_argument('--executable',default=str(WORK/'replay'));parser.add_argument('--fixtures',default=str(BASE/'fixtures.json'));parser.add_argument('--fixture-sha256');options=parser.parse_args();mode=options.mode;LOG=OUT/'runs'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ');LOG.mkdir(parents=True)
def run(argv,name):
    t=time.monotonic();start=datetime.datetime.now(datetime.timezone.utc).isoformat();p=subprocess.run(argv,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(LOG/(name+'.log')).write_text(p.stdout);(LOG/(name+'.command.json')).write_text(json.dumps(dict(argv=argv,start_utc=start,end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),seconds=time.monotonic()-t,returncode=p.returncode),indent=2)+'\n');assert p.returncode==0,(name,p.returncode,p.stdout[-4000:]);return p.stdout
if mode=='native':print(run(['uc-library/.venv/bin/python',str(BASE/'native.py')],'native'))
elif mode=='format':
    print(run(['uc-library/.venv/bin/clang-format','--version'],'formatter-version'));print(run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*FORMAT],'format'))
elif mode=='compile':
    print(run(['c++','--version'],'compiler-version').splitlines()[0]);objects=[]
    for i,s in enumerate(SOURCES):
        obj=str(WORK/f'unit{i}.o');objects.append(obj);run(['c++',*FLAGS,'-MMD','-MF',str(WORK/f'unit{i}.d'),'-c',s,'-o',obj],f'compile{i}')
    run(['c++',*objects,*LINKS,'-Wl,--wrap=inflateInit2_','-Wl,--wrap=inflate','-Wl,--wrap=inflateEnd','-Wl,--wrap=open','-Wl,--wrap=ioctl','-Wl,--wrap=socket','-o',str(WORK/'replay')],'link');print('Compiled owned source and actual canonical provider units')
elif mode=='symbols':
    out=run(['nm','--defined-only',str(WORK/'unit0.o')],'symbols');names={x.split()[-1] for x in out.splitlines() if x.split()};required=[x['mangled'] for x in json.loads((BASE/'fixtures.json').read_text())['ranges'][:2]]
    assert all(x in names for x in required);(OUT/'symbols.json').write_text(json.dumps(dict(required=required,names_match=True,namespace_verified=True,object_format='ELF64 x86_64; no decoration',original_arm_abi_verified=False),indent=2)+'\n');print('Exact original updater mangled names present')
elif mode=='regressions':
    objects=[str(WORK/f'unit{i}.o') for i in range(9)]
    for name,source,args in [('nonprogramming','uc-library/candidates/rolling200_02_stage03_w06/replay.cpp',['evidence/recovery/2026-11-05/rolling200-02/updater02/fixtures.txt']),('lifecycle','uc-library/tests/recovery/FPGADeletingDestructorReplay.cpp',[])]:
        obj=str(WORK/(name+'.o'));exe=str(WORK/name)
        run(['c++',*FLAGS,'-MMD','-MF',str(WORK/(name+'.d')),'-c',source,'-o',obj],name+'-compile')
        run(['c++',*objects,obj,'-Wl,--start-group',*ARCHIVES,'temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a','-Wl,--end-group',*LINKS[len(ARCHIVES):],'-o',exe],name+'-link')
        print(run([exe,*args],name+'-replay'))
elif mode=='replay':
    fixture_path=Path(options.fixtures);fixture_hash=hashlib.sha256(fixture_path.read_bytes()).hexdigest();assert not options.fixture_sha256 or fixture_hash==options.fixture_sha256;fixture=json.loads(fixture_path.read_text());results=[]
    for c in fixture['cases']:
        argv=[options.executable,c['mode'],str(c.get('size',0)),c.get('fault','none'),str(c.get('start_ms',100)),str(c.get('step_ms',400)),str(c.get('reply_after',0)),str(c.get('cancel',0)),str(c.get('length',4)),str(int(c.get('null',False))),str(c.get('timeout',4000)),str(int(c.get('message',True))),str(int(c.get('delegate_reply',False)))]
        actual=json.loads(run(argv,c['name']));expected=c['expected'];keys=['return','packets','messages','debug','sleeps','state','closes','opens','reads']
        if 'delegated' in expected:
            keys=['return','packets','messages','debug','state'];assert actual['pumps'] and actual['sleeps'];assert bool(actual['notices']) != bool(c.get('delegate_reply'))
        mismatches={k:dict(expected=expected[k],actual=actual[k]) for k in keys if expected[k]!=actual[k]}
        assert not mismatches,(c['name'],mismatches)
        results.append(dict(name=c['name'],compared=keys,actual=actual,passed=True))
    # Separate safety adaptation: actual zlib error returns -1, native loop is
    # deliberately not allowed to access unbounded memory or execute indefinitely.
    argv=[options.executable,'update','4','negative_read','100','400','0','0','4','0','4000','1','0'];a=json.loads(run(argv,'negative-read-adaptation'));assert a['return']==2003 and a['closes']==2 and len(a['packets'])==1
    results.append(dict(name='negative-read-adaptation',actual=a,passed=True,native_equivalence=False));(OUT/'replay.json').write_text(json.dumps(dict(cases=results,fixture_sha256=fixture_hash),indent=2)+'\n');print('PASS',len(results),'native coordinator/wait comparisons and explicit read-error safety adaptation; real providers, captured transport')
else:raise SystemExit('unknown mode')
