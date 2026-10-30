"""Prepare fixed metadata admission guards from the reviewed registrar wrapper."""
from pathlib import Path
import ast,hashlib,json
source=Path('uc-library/tools/recovery/admit_registrar_batch.py');target=source.with_name('admit_metadata_batch.py');assert not target.exists()
text=source.read_text()
changes=[('registrar-batch','metadata-batch'),('uc-network-registrar-services','uc-network-server-metadata'),('noaa-spi-service-registrar','noaa-spi-service-metadata'),('==146','==150'),("headers['headers']==91","headers['headers']==93"),('(639,343,485)','(639,343,507)'),('(639,467)','(639,491)'),('pending=485','pending=507'),('len(added)==18','len(added)==16'),('})==9','})==8'),('new_pending_records=18','new_pending_records=16'),('new_pending_unique_names=9','new_pending_unique_names=8')]
for old,new in changes:
    assert old in text,old;text=text.replace(old,new)
ast.parse(text);target.write_text(text)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
Path('evidence/recovery/2026-10-28/metadata-batch/admission-derivation.json').write_text(json.dumps(dict(source=str(source),source_sha256=sha(source),derivative=str(target),derivative_sha256=sha(target),changes=changes),indent=2)+'\n')
