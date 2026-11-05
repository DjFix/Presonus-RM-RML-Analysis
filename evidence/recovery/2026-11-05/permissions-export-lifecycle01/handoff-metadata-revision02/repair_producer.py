import hashlib,importlib.util,json,shutil
from pathlib import Path
base=Path('uc-library/candidates/permissions_export_lifecycle')
ev=Path('evidence/recovery/2026-11-05/permissions-export-lifecycle01/handoff-metadata-revision02')
ev.mkdir(exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
tool=Path('uc-library/tools/recovery/accept_worker.py')
canonical=Path('/home/rs/projects/opencs/ai-line-analysis')/tool
assert sha(tool)==sha(canonical)
spec=importlib.util.spec_from_file_location('accept_worker',tool);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
rows=[]
for suf in ['01','04','05','06']:
 p=base/suf/'HANDOFF.json';old=ev/('HANDOFF-'+suf+'-revision01.json');shutil.copyfile(p,old)
 data=json.loads(p.read_text())
 for a in data['artifacts']:
  if a['path']=='uc-library/tests/recovery/PermissionsExportLifecycleReplay.cpp':a['kind']='test'
  if a['path']==str(base/'checks.py'):a['kind']='replay'
 p.write_text(json.dumps(data,indent=2)+'\n')
 module.validate(data)
 rows.append(dict(path=str(p),old_path=str(old),old_sha256=sha(old),new_sha256=sha(p),schema_validation='passed without executing checks',changes=['Replay C++ classification source -> test','checks.py classification producer -> replay']))
log=Path('temp/recovery-work/root-acceptance09b/01.log')
if log.exists():shutil.copyfile(log,ev/'root-acceptance09b-01.log')
receipt=dict(version=1,date='2026-11-05',reason='Root acceptance rejected missing test artifact kind before any checks executed. Required replay kind also repaired.',previous_commit='9cbdb862f97e8a6993a810b46fd93079967ccf7e',validator=str(tool),validator_sha256=sha(tool),validator_byte_identical_to_canonical=True,source_or_replay_code_changed=False,prior_execution_proof_preserved=True,rerun_execution=False,handoffs=rows)
(ev/'revision.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
