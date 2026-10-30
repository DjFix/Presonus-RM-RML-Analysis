"""Guarded paired Control/UC file-services application; no ledger admission."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

repo=Path('/home/rs/projects/opencs/ai-line-analysis')
lib=repo/'uc-library'
control=lib/'candidates/panel-control-base'
files=lib/'candidates/uc-file-services'
seal=files/'validation/seals/file-services-validation-01'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
cp=control/'CONTROLLED-APPLY.json';fp=seal/'controlled-apply.json'
assert sha(cp)=='7ac93468dbad90d45795cf1c8562eddd0537a3a413322c83fe60aa70c40e967a'
assert sha(fp)=='75002cb06f594c87729714bf97dcc569600ee683aad0cf4386de2e9b5fd570f1'
c=json.loads(cp.read_text());f=json.loads(fp.read_text())
assert (c['new_ready_entries'],c['new_pending_entries'],c['new_ready_mangles'])==(14,42,7)
assert (f['ready_proposal'],f['pending'],f['existing_header_changes'])==(34,20,False)
for name,digest in c['frozen_proofs'].items():assert sha(control/name)==digest
for name,digest in c['base_product_bindings'].items():assert sha(lib/name)==digest
assert sha(control/'reseal_active.py')==c['active_reseal_sha256']=='64acfeae8ee14fbf9a877cf6d1a2e05303a0d8e46f5520144c1eee9de98a0029'
assert sha(files/'active_reseal.py')=='fbaf59ba40a6b209185f177db192a25f40e04d98b991bcf48a93873077d0804b'
assert sha(files/'seal_common.py')=='6c70f328af3af7336a2bca74ef27480b0f7da318713d714f34a2b98048d11435'
for name,digest in {
 'lifecycle-ready-validation.json':'c807dbce372f7e27534c5ec2c0794d9b6dc269a1a8c7af7bfe50b9f2aaf0a859',
 'ordinary-pending-validation.json':'7d99e48e21a1feed30b52ff39c3e9be9a926d99b988f7cfd8325bbc95a2b6332',
 'lifecycle-ready-fragment.json':'436cf405c631a08343b2905248472cf979efe63ddd60d2233b9fdaa01062ad5e',
 'ordinary-pending-fragment.json':'7a565b11ec123ce3c2b238962c96abe3e89bc593984e2c303f906879a68ecffa',
}.items():assert sha(seal/name)==digest
for proof_path in (control/'validation/validation.json',control/'validation/pending-validation.json',seal/'lifecycle-ready-validation.json',seal/'ordinary-pending-validation.json'):
    proof=json.loads(proof_path.read_text())
    for path,digest in proof['sources'].items():assert sha(lib/path)==digest,path
    for path,digest in proof.get('repository_sources',{}).items():assert sha(repo/path)==digest,path
copies=[(control/name,row['target'],row['sha256']) for name,row in c['copies'].items()]
assert all(row['active_sha256'] is None for row in c['copies'].values())
copies.extend((files/row['source'],row['destination'],row['sha256']) for row in f['products'])
assert all(row['required_destination']=='absent' for row in f['products'])
assert len(copies)==len({target for _,target,_ in copies})==9
for source,target,digest in copies:
    assert sha(source)==digest and not (lib/target).exists(),target
fixtures=[(control/name,target,c['fixture_sha256']) for name,target in c['fixture_copies'].items()]
fixtures.append((seal/'fixtures.jsonl','validation/uc-file-services/fixtures.jsonl','fefba1cba60c677b7611bd0f6077750b1ec3ea696330ca100eec1f9ab790e9da'))
assert len(fixtures)==2
for source,target,digest in fixtures:assert sha(source)==digest and not (lib/target).exists(),target
build_files=('CMakeLists.txt','cmake/ProductionSourceGroups.cmake')
affected={}
for label,name,digest in [('ready','ready-functions.json','05d9b98c8ab2c9a1d766397d0f82fe88a0c036491adf153c52e659d1be2c5090'),('pending','compiled-functions.json','211c10482f01e37954b89d345ba87a7f29e004503068d92ba544cb3a6c541d27')]:
    path=lib/'validation'/name;assert sha(path)==digest
    rows=json.loads(path.read_text())['functions']
    affected[label]=[dict(original_elf_sha256=r['original_elf_sha256'],mangled=r['mangled'],validation=r['validation'],validation_sha256=r['validation_sha256']) for r in rows if any(n in r['sources'] for n in build_files)]
assert (len(affected['ready']),len(affected['pending']))==(1,4)
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
evidence=repo/'evidence/recovery/2026-10-27/control-file-application'/stamp
evidence.mkdir(parents=True,exist_ok=False)
for name in build_files:
    dest=evidence/'before'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(lib/name,dest)
phase=repo/'evidence/recovery/2026-10-27/control-file-services-root';phase.mkdir(parents=True,exist_ok=True)
(phase/'dependency-review.json').write_text(json.dumps(dict(build_file_preimages={n:sha(lib/n) for n in build_files},affected=affected,existing_headers_replaced=False),indent=2)+'\n')
for source,target,_ in copies+fixtures:
    dest=lib/target;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
shutil.copyfile(cp,evidence/'control-controlled-apply.json');shutil.copyfile(fp,evidence/'file-controlled-apply.json')
(evidence/'application.json').write_text(json.dumps(dict(products={t:sha(lib/t) for _,t,_ in copies},fixtures={t:sha(lib/t) for _,t,_ in fixtures},planned_new_ready=48,planned_new_pending=62,refreshed_ready=1,refreshed_pending=4,admission_performed=False),indent=2)+'\n')
targets=[t for _,t,_ in copies]
(lib/'validation/format-control-file-paths.json').write_text(json.dumps([p for p in targets if Path(p).suffix in ('.cpp','.hpp','.h')],indent=2)+'\n')
(lib/'validation/integration-control-file-additions.json').write_text(json.dumps(sorted(set(targets+[t for _,t,_ in fixtures]+list(build_files))),indent=2)+'\n')
print(json.dumps(dict(applied=9,fixtures=2,old_build_proofs_requiring_refresh=5,evidence=str(evidence.relative_to(repo)))))
