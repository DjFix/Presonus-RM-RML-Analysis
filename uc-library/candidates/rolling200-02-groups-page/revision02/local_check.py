"""Isolated adapter validation; canonical CMake uses existing role target only.
Baseline role archive is copied and its two affected members refreshed in scratch.
This is a local validation artifact, never a replacement for Root's OBJECT build.
"""
import datetime,hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
BASE=Path('uc-library/candidates/rolling200-02-groups-page/revision02');WORK=Path('temp/recovery-work/rolling200-02/groups-page/canonical02');OUT=Path('evidence/recovery/2026-11-05/rolling200-02/groups-page/revision02');PARENT=OUT.parent
LOG=OUT/'checks'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ');LOG.mkdir(parents=True,exist_ok=False)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
FLAGS=['-std=c++17','-O2','-fno-rtti','-fno-instrument-functions','-fno-fast-math','-ffp-contract=off','-Wno-multichar','-Iuc-library/include','-Ithird_party/ccl-framework']
PRODUCTION=['uc-library/src/Presonus/Surface/GroupsPageComponent.cpp','uc-library/src/Presonus/Surface/GroupsPageRecovery.cpp'];ROLE=Path('temp/core-upstream/root-integration-01/libpresonus_cs18_components.a')
def run(argv,name):
 env=os.environ.copy();env['TMPDIR']=str(WORK.resolve());start=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic();r=subprocess.run(argv,text=True,capture_output=True,env=env);(LOG/(name+'.stdout')).write_text(r.stdout);(LOG/(name+'.stderr')).write_text(r.stderr);(LOG/(name+'.json')).write_text(json.dumps(dict(argv=argv,start_utc=start,seconds=time.monotonic()-t,returncode=r.returncode,producer_sha256=sha(__file__),inputs={p:sha(p) for p in PRODUCTION+[str(BASE/'canonical_replay.cpp'),str(BASE/'canonical_verify.py')]}),indent=2)+'\n');assert r.returncode==0,(argv,r.returncode,r.stderr);print(r.stdout,end='');return r.stdout
mode=sys.argv[1]
if mode=='format':
 run(['uc-library/.venv/bin/clang-format','--version'],'version');run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',str(BASE/'canonical_replay.cpp')],'format')
elif mode=='compile':
 run(['c++','--version'],'compiler');shutil.copy2(ROLE,WORK/ROLE.name)
 for source in PRODUCTION:
  obj=WORK/(Path(source).name+'.o');run(['c++',*FLAGS,'-MMD','-MF',str(obj)+'.d','-c',source,'-o',str(obj)],Path(source).stem);run(['ar','r',str(WORK/ROLE.name),str(obj)],'archive-'+Path(source).stem)
 run(['c++',*FLAGS,str(BASE/'canonical_replay.cpp'),str(WORK/ROLE.name),'temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a','/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lz','-lssl','-lcrypto','temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so','-pthread','-ldl','-lm','-Wl,-rpath,'+str(Path('temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu').resolve()),'-o',str(WORK/'replay')],'link')
 (OUT/'local-archive.json').write_text(json.dumps(dict(baseline_role_archive=str(ROLE),baseline_sha256=sha(ROLE),scratch_role_archive=str(WORK/ROLE.name),scratch_sha256=sha(WORK/ROLE.name),refreshed_members=[Path(p).name+'.o' for p in PRODUCTION],production_test_source_duplication=False,canonical_build_claim=False,reason='Isolated role-archive surrogate for adapter verification only; Root must rebuild existing production OBJECT partitions after integration.'),indent=2)+'\n')
elif mode=='symbols':
 for source in PRODUCTION:
  obj=WORK/(Path(source).name+'.o');out=run(['nm','-u',str(obj)],'undefined-'+Path(source).stem);assert '__cyg_profile' not in out
 out=run(['nm','--defined-only',str(WORK/'replay')],'executable-symbols');assert '__cyg_profile' not in out
elif mode=='replay':
 a=['uc-library/.venv/bin/python',str(BASE/'canonical_verify.py'),'--executable',str(WORK/'replay'),'--fixtures',str(PARENT/'native.json'),'--fixture-sha256',sha(PARENT/'native.json'),'--inputs',str(PARENT/'inputs.txt'),'--inputs-sha256',sha(PARENT/'inputs.txt')];out=run(a,'canonical-replay');(OUT/'replay.json').write_text(json.dumps(json.loads(out),indent=2)+'\n')
else:raise SystemExit('format/compile/symbols/replay')
