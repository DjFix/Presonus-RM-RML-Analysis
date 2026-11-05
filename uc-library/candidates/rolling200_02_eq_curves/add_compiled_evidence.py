"""Append explicit compiled-symbol evidence without changing original local proof."""
from pathlib import Path
import subprocess,json,hashlib,shutil,datetime,importlib.util
R=Path.cwd();A=Path(__file__).resolve().parent;E=R/'evidence/recovery/2026-11-05/rolling200-02/eq-curves/local-final01';T=R/'uc-library/tests/recovery/rolling200-02/eq-curves';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();rel=lambda p:str(p.relative_to(R))
exe=R/'temp/recovery-work/rolling200-02/eq-curves/driver'
symbols=subprocess.check_output(['nm','--defined-only',str(exe)],text=True);(E/'compiled-symbols.txt').write_text(symbols)
proof=json.loads((E/'LOCAL_PROOF.json').read_text());names={x.split()[-1] for x in symbols.splitlines() if x.split()};originals=proof['originals'];assert all(o['mangled'] in names for o in originals)
# Preserve direct execution output from the earlier required dependency replay.
p=subprocess.run(['uc-library/.venv/bin/python','uc-library/tests/recovery/rolling200-02/eq-control/check.py','replay'],cwd=R,text=True,capture_output=True);assert p.returncode==0;(E/'existing-EQ-regression.stdout').write_text(p.stdout);(E/'existing-EQ-regression.stderr').write_text(p.stderr)
data={'date':datetime.datetime.now(datetime.timezone.utc).isoformat(),'binary':rel(exe),'binary_sha256':sha(exe),'compiled_symbols':{o['mangled']:{'present':True,'object_format':'Linux host ELF; no leading object-format underscore decoration','ordinary_return_declaration_verified':False,'original_ARM_ABI_verified':False} for o in originals},'nm_argv':['nm','--defined-only',rel(exe)],'nm_output':rel(E/'compiled-symbols.txt'),'nm_output_sha256':sha(E/'compiled-symbols.txt'),'producer':rel(Path(__file__).resolve()),'producer_sha256':sha(Path(__file__).resolve()),'original_proof':rel(E/'LOCAL_PROOF.json'),'original_proof_sha256':sha(E/'LOCAL_PROOF.json'),'existing_EQ_dependency_replay':{'cases':1038,'passed':True,'argv':['uc-library/.venv/bin/python','uc-library/tests/recovery/rolling200-02/eq-control/check.py','replay']},'numerical_replay':json.loads((R/'evidence/recovery/2026-11-05/rolling200-02/eq-curves/checks/curves.stdout').read_text())}
(E/'COMPILED_EVIDENCE.json').write_text(json.dumps(data,indent=2)+'\n')
for handoff in sorted(A.glob('*/HANDOFF.json')):
 j=json.loads(handoff.read_text())
 for f in [E/'COMPILED_EVIDENCE.json',E/'compiled-symbols.txt',E/'existing-EQ-regression.stdout',E/'existing-EQ-regression.stderr',Path(__file__).resolve()]:j['artifacts'].append({'kind':'proof' if f.suffix!='.py' else 'producer','path':rel(f),'sha256':sha(f)})
 handoff.write_text(json.dumps(j,indent=2)+'\n')
spec=importlib.util.spec_from_file_location('accept_worker',R/'uc-library/tools/recovery/accept_worker.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
for handoff in sorted(A.glob('*/HANDOFF.json')):module.validate(json.loads(handoff.read_text()));print('VALID',rel(handoff))
