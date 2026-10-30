"""Prepare phase-specific unchanged raw and workload audit derivatives."""
from pathlib import Path
import ast,hashlib,json
jobs=[
('uc-library/candidates/efm-fader-control-dispatch/tools/seal_raw_root_queries.py','uc-library/candidates/efm-fader-control-dispatch/tools/seal_raw_root_registrar.py',[('queries-batch','registrar-batch'),('==145','==146'),('canonical_ctest_count=145','canonical_ctest_count=146')]),
('uc-library/tools/recovery/count_queries_unique.py','uc-library/tools/recovery/count_registrar_unique.py',[('queries-batch','registrar-batch')]),
('uc-library/tools/recovery/audit_queries_raw.py','uc-library/tools/recovery/audit_registrar_raw.py',[('queries-batch','registrar-batch')])]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();receipt=[]
for source,target,changes in jobs:
    source,target=Path(source),Path(target);assert not target.exists();text=source.read_text()
    for old,new in changes:
        assert old in text; text=text.replace(old,new)
    ast.parse(text);target.write_text(text)
    receipt.append(dict(source=str(source),source_sha256=sha(source),derivative=str(target),derivative_sha256=sha(target),changes=changes))
Path('evidence/recovery/2026-10-28/registrar-batch/closure-derivatives.json').write_text(json.dumps(receipt,indent=2)+'\n')
