"""Complete missing path lists after guarded source application already succeeded."""
from pathlib import Path
import hashlib,json
repo=Path.cwd().resolve();lib=repo/'uc-library';out=repo/'evidence/recovery/2026-10-28/device-eq-batch'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
receipt=json.loads((out/'application-device.json').read_text());products=receipt['products']
assert len(products)==10
for name,row in products.items():assert sha(lib/name)==row['applied_sha256'],name
formatter=lib/'validation/format-device-eq-paths.json';integration=lib/'validation/integration-device-eq-additions.json'
assert not formatter.exists() and not integration.exists()
producer=lib/'tools/recovery/apply_device_controls.py';before=producer.read_bytes();backup=out/'apply_device_controls.before-list-fix.py';assert not backup.exists();backup.write_bytes(before)
text=before.decode()
for name in ['format-device-eq-paths.json','integration-device-eq-additions.json']:
    old=f"paths=read(lib/'validation/{name}')"
    new=f"paths=read(lib/'validation/{name}') if (lib/'validation/{name}').exists() else []"
    assert text.count(old)==1;text=text.replace(old,new)
producer.write_text(text)
cpp=[name for name in products if Path(name).suffix in ('.cpp','.hpp','.h')]
formatter.write_text(json.dumps(sorted(set(cpp+[products[name]['source'] for name in cpp])),indent=2)+'\n')
integration.write_text(json.dumps(sorted(products),indent=2)+'\n')
report=dict(repaired=True,source_cpp_changed=False,products_reapplied=False,applied_product_hashes_verified=10,producer_before_sha256=hashlib.sha256(before).hexdigest(),producer_after_sha256=sha(producer),failure='Append-only application derivative expected existing new-batch format/integration path lists; source application completed before list step',formatter_list_sha256=sha(formatter),integration_list_sha256=sha(integration))
(out/'path-list-initialization-fix.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
