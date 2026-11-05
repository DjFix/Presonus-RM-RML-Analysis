"""Local, noninteractive, non-programming handoff checks; no ledger mutations."""
import sys,json,hashlib,subprocess,datetime,time,platform
from pathlib import Path
BASE=Path('uc-library/candidates/rolling200_02_stage03_w06');OUT=Path('evidence/recovery/2026-11-05/rolling200-02/updater02');WORK=Path('temp/recovery-work/rolling200-02/updater01');OUT.mkdir(parents=True,exist_ok=True);WORK.mkdir(parents=True,exist_ok=True)
SOURCES=['uc-library/src/Presonus/NOAA/TCardFPGAUpdater.cpp','uc-library/src/Presonus/NOAA/SysexReceiver.cpp','uc-library/src/Presonus/NOAA/SysexReceiverWait.cpp',str(BASE/'replay.cpp')]
FORMAT=['uc-library/include/presonus/noaa/TCardFPGAUpdater.hpp',SOURCES[0],SOURCES[-1]]
SDK='temp/core-upstream/root-integration-01/upstream-core/sdk';ARCHIVES=['temp/core-upstream/root-integration-01/libpresonus_uc.a',SDK+'/lib/libcorelib.a',SDK+'/lib/libpresonus_core_allocator.a'];LINKS=ARCHIVES+['/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lz','-lssl','-lcrypto','temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so','-pthread','-ldl','-lm','-Wl,-rpath,'+str(Path('temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu').resolve())]
FLAGS=['-std=c++17','-O2','-Iuc-library/include','-Ithird_party/ccl-framework'];PACKETS=Path('temp/recovery-work/rolling200-02/implementation-plan01/packets-batch03/packets')
LOG=OUT/'check-runs'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ');LOG.mkdir(parents=True,exist_ok=False)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(argv,name):
 start=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic();p=subprocess.run(argv,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(LOG/(name+'.log')).write_text(p.stdout);(LOG/(name+'.command.json')).write_text(json.dumps(dict(argv=argv,start_utc=start,end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),seconds=time.monotonic()-t,returncode=p.returncode),indent=2)+'\n');print(p.stdout[-2000:],end='');assert p.returncode==0,(argv,p.returncode);return p.stdout
mode=sys.argv[1]
if mode=='oracle':run(['uc-library/.venv/bin/python',str(BASE/'oracle.py')],'oracle')
elif mode=='format':
 run(['uc-library/.venv/bin/clang-format','--version'],'formatter-version');run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*FORMAT],'format')
elif mode=='compile':
 run(['c++','--version'],'compiler-version');objects=[]
 for i,s in enumerate(SOURCES):
  obj=str(WORK/f'unit{i}.o');objects.append(obj);run(['c++',*FLAGS,'-MMD','-MF',str(WORK/f'unit{i}.d'),'-c',s,'-o',obj],f'compile{i}')
 run(['c++',*objects,*LINKS,'-o',str(WORK/'replay')],'link')
elif mode=='symbols':
 out=run(['nm','--defined-only',str(WORK/'unit0.o')],'symbols');names={l.split()[-1] for l in out.splitlines() if l.split()};required=[]
 for i in [1,2,5,6,7,8,9,10]:
  r=json.loads((PACKETS/f'rolling200_02_impl_updater_{i:02d}'/'request.json').read_text());n=r['targets'][0]['mangled'];assert n in names,n;required.append(n)
 excluded=['_ZN8Presonus4NOAA16TCardFPGAUpdater19waitFirmwareCommandEPhiPKcx','_ZN8Presonus4NOAA16TCardFPGAUpdater6updateEv','_ZN8Presonus4NOAA16TCardFPGAUpdater20cancelPortableUpdateEb']
 for n in excluded:assert n not in names,n
 undefined=run(['nm','-u',str(WORK/'unit0.o')],'undefined-symbols');assert 'FirmwareBundle' not in undefined and 'pack32' not in undefined
 (OUT/'symbols.json').write_text(json.dumps(dict(checked_originals=required,object_format='ELF64 x86_64; no name decoration',names_match=True,excluded_parked_methods_absent=excluded,firmware_bundle_and_pack32_dependencies_absent=True,original_arm_abi_verified=False),indent=2)+'\n')
elif mode=='replay':run([str(WORK/'replay'),str(OUT/'fixtures.txt')],'replay')
elif mode=='seal':
 deps=set(SOURCES+FORMAT+[str(BASE/'oracle.py'),str(BASE/'verify.py')]+ARCHIVES)
 for i in range(len(SOURCES)):
  s=(WORK/f'unit{i}.d').read_text().replace('\\\n',' ');deps.update(x for x in s.split(':',1)[1].split() if Path(x).is_file() and not x.startswith('/usr/'))
 deps.update(['uc-library/src/portable/dice/CclResponseServices.cpp','third_party/ccl-framework/core/system/coretime.h','third_party/ccl-framework/core/system/corethread.h','third_party/ccl-framework/core/system/coredebug.cpp','uc-library/src/Presonus/NOAA/TCardSPIPackets.cpp','uc-library/src/Presonus/NOAA/TCardSPIService.cpp'])
 dependency_hashes={p:sha(p) for p in sorted(deps)}
 native=json.loads((OUT/'native-observations.json').read_text());checks={str(p.relative_to(OUT)):json.loads(p.read_text()) for p in OUT.rglob('*.command.json')};assert all(c['returncode']==0 for c in checks.values())
 proof=dict(version=1,previous_delivery_history='evidence/recovery/2026-11-05/rolling200-02/updater-history01/MANIFEST.json',previous_delivery_history_sha256=sha('evidence/recovery/2026-11-05/rolling200-02/updater-history01/MANIFEST.json'),excluded_parked_definition_artifact='uc-library/candidates/rolling200_02_stage03_w06/parked_methods.cpp',excluded_parked_definition_sha256=sha(BASE/'parked_methods.cpp'),scope='bounded portable source port, eight non-programming identities; no readiness admission',host=platform.platform(),elf_sha256=native['elf_sha256'],ranges=native['ranges'],native_original_cases=len(native['cases']),per_function_cases={str(i):sum(c['target']==i for c in native['cases']) for i in [1,2,5,6,7,8,9,10]},fixture_sha256=sha(OUT/'fixtures.txt'),sources=dependency_hashes,oracle_producer_sha256=sha(BASE/'oracle.py'),replay_producer_sha256=sha(BASE/'replay.cpp'),checks=checks,namespace_and_mangling_verified=True,compilation_and_replay_passed=True,formatting_verified=True,original_declaration_verified=False,original_arm_abi_verified=False,hardware_verified=False,core_binary_bodies_executed=False,programming_or_transport_bodies_executed=False,unicorn_version=native['unicorn_version'],limitations=['Ordinary return types and exact original declarations unresolved; matching mangling is not ARM ABI/layout evidence.','Lifecycle existing-singleton, normal-return domain only. Native constructor/base/register/unregister boundaries are scripted, actual portable CCL vector/lock provider runs in C++. Native allocator and exception paths excluded; D0 not executed or admitted.','Native listener/time/debug/sleep boundaries are scripted. Soft-float arithmetic executes original ELF instructions; no Core implementation recovered/executed.','Mutable epoch is independent portable storage; original cross-class global linkage/concurrency not established.','waitFirmwareCommand, update and their exclusive helpers are absent from the active production TU; definitions preserved in nonproduction parked_methods.cpp. No native/replay execution or handoff for those methods. Header declarations remain pending.'])
 (OUT/'proof.json').write_text(json.dumps(proof,indent=2)+'\n');print('sealed',OUT/'proof.json')
else:raise SystemExit('unknown mode')
