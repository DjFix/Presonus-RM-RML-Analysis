"""Prepare a fixed guarded device application from the prior reviewed recipe."""
from pathlib import Path
import ast,hashlib,json
source=Path('uc-library/tools/recovery/apply_followon_programmer.py');target=source.with_name('apply_device_controls.py');assert not target.exists()
text=source.read_text()
changes=[('followon-batch','device-eq-batch'),('dice-programmer-transactions','dice-programmer-open-close'),('ce7c0e3071b3e33215b907ebaab76556e8b06becc379901e9ddb05ac6206f37a','5f7fa0632c546728ecd841f62297827e49d6e1813ed68748730164e93674e8dd'),('==[80,28,10]','==[82,31,10]'),('programmer_services.hpp','programmer_device_services.hpp'),('dice_programmer_transactions','dice_programmer_device'),('validation/dice-programmer-open-close/','validation/dice-programmer-device/'),('==(4,2)','==(4,9)'),('suites=142,headers=90','suites=148,headers=92'),('programmer_refresh_pending=2','programmer_refresh_pending=9'),('before-programmer','before-device'),('application-programmer','application-device'),('affected-programmer-source-closure','affected-device-source-closure'),('format-followon-paths','format-device-eq-paths'),('integration-followon-additions','integration-device-eq-additions')]
for old,new in changes:
    assert old in text,old;text=text.replace(old,new)
old='  target_link_options(dice_programmer_device_bridge PRIVATE -Wl,--wrap=ioctl)'
new='''  target_link_options(dice_programmer_device_bridge PRIVATE
    -Wl,--wrap=open -Wl,--wrap=__open_2 -Wl,--wrap=close -Wl,--wrap=ioctl)'''
assert text.count(old)==1;text=text.replace(old,new)
ast.parse(text);target.write_text(text)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
Path('evidence/recovery/2026-10-28/device-eq-batch/application-derivation.json').write_text(json.dumps(dict(source=str(source),source_sha256=sha(source),derivative=str(target),derivative_sha256=sha(target),changes=changes,link_wrappers=['open','__open_2','close','ioctl']),indent=2)+'\n')
