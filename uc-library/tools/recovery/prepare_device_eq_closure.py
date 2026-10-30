"""Prepare unchanged raw and workload audit gates for the device/EQ batch."""
from pathlib import Path
import ast,hashlib,json
jobs=[
('uc-library/candidates/efm-fader-control-dispatch/tools/seal_raw_root_registrar.py','uc-library/candidates/efm-fader-control-dispatch/tools/seal_raw_root_device_eq.py',[('registrar-batch','device-eq-batch'),('==146','==149'),('canonical_ctest_count=146','canonical_ctest_count=149')]),
('uc-library/tools/recovery/count_registrar_unique.py','uc-library/tools/recovery/count_device_eq_unique.py',[('registrar-batch','device-eq-batch')]),
('uc-library/tools/recovery/audit_registrar_raw.py','uc-library/tools/recovery/audit_device_eq_raw.py',[('registrar-batch','device-eq-batch')])]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();receipt=[]
for source,target,changes in jobs:
    source,target=Path(source),Path(target);assert not target.exists();text=source.read_text()
    for old,new in changes:
        assert old in text;text=text.replace(old,new)
    ast.parse(text);target.write_text(text)
    receipt.append(dict(source=str(source),source_sha256=sha(source),derivative=str(target),derivative_sha256=sha(target),changes=changes))
Path('evidence/recovery/2026-10-28/device-eq-batch/closure-derivatives.json').write_text(json.dumps(receipt,indent=2)+'\n')
