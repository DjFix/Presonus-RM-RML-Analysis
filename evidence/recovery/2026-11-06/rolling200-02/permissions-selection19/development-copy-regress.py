from pathlib import Path
import hashlib,json,shutil,subprocess,importlib.util
root=Path('/home/rs/projects/opencs/ai-line-analysis');local=Path.cwd();E=Path('evidence/recovery/2026-11-06/rolling200-02/permissions-selection19');moves=[]
for folder in ['evidence/recovery/2026-11-05/permissions-lists01','evidence/recovery/2026-11-05/permissions-readonly01','evidence/recovery/2026-11-05/permissions-export-lifecycle01','evidence/recovery/2026-11-05/rolling200-02/equivalence37/constructor59']:
 for source in (root/folder).rglob('*'):
  if not source.is_file() or (source.name not in ['native-fixtures.json','native-fixture.txt','native-proof.json','ROOT_REVIEW.json','PROPOSED_REVIEW.json','RELEASE_MANIFEST.json','RELEASE_RECEIPT.json']):continue
  relative=source.relative_to(root);target=local/relative;digest=hashlib.sha256(source.read_bytes()).hexdigest()
  if target.exists():assert hashlib.sha256(target.read_bytes()).hexdigest()==digest
  else:target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
  assert hashlib.sha256(target.read_bytes()).hexdigest()==digest
  moves.append(dict(source=str(source),destination=str(target),relative=str(relative),sha256=digest,size=source.stat().st_size,reason='Exact immutable historical regression/equivalence input copied; no overwrite of differing evidence'))
(E/'copied-inputs.json').write_text(json.dumps(moves,indent=2)+'\n')
spec=importlib.util.spec_from_file_location('checks','uc-library/tests/recovery/permissions_selection/check.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
flags=['/usr/bin/c++','-std=c++17','-O2','-fno-lto','-ffunction-sections','-fdata-sections','-fno-rtti','-pthread','-Ulinux','-Iuc-library/include','-I'+str(m.SDK/'include/presonus-core-5')]
for name,source in [('readonly','PermissionsReadonlyReplay'),('lists','PermissionsListsReplay'),('lifecycle','PermissionsExportLifecycleReplay')]:
 obj=m.WORK/(source+'.o');exe=m.WORK/name;m.run(flags+['-c','uc-library/tests/recovery/'+source+'.cpp','-o',obj]);extra=[]
 if name=='lists':
  link=m.WORK/'LinkableComponent.o';m.run(flags+['-c','uc-library/src/Presonus/LinkableComponent.cpp','-o',link]);extra.append(link)
 m.run(flags+[m.WORK/'PermissionsComponent.o',m.WORK/'ClientSubscription.o',m.WORK/'MixerComponentBase.o',obj]+extra+['-Wl,--gc-sections','-Wl,--start-group','temp/core-upstream/root-integration-01/libpresonus_rm_components.a',m.SDK/'lib/libcorelib.a',m.SDK/'lib/libpresonus_core_allocator.a','temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a','-Wl,--end-group','-pthread','-ldl','-lm','-lz','-o',exe])
 if name=='readonly':print(m.run([exe,'evidence/recovery/2026-11-05/permissions-readonly01/native-fixture.txt']))
 else:
  f='uc-library/candidates/'+('rolling200_02_permissions_lists' if name=='lists' else 'permissions_export_lifecycle')+'/checks.py';spec=importlib.util.spec_from_file_location(name,f);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.WORK=m.WORK;module.replay(str(exe),'evidence/recovery/2026-11-05/'+('permissions-lists01' if name=='lists' else 'permissions-export-lifecycle01')+'/native-fixtures.json')
