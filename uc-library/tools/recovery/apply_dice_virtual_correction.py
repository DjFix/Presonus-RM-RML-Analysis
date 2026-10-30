"""Apply the reviewed, versioned receiver virtual declaration correction."""
from pathlib import Path
import hashlib,json,shutil

repo=Path.cwd().resolve();lib=repo/'uc-library'
out=repo/'evidence/recovery/2026-10-28/continuation-batch/dice-interface-correction'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
mapfile=lib/'candidates/dice-continuation/CONTROLLED-APPLY.json'
assert sha(mapfile)=='45adf2ad222a59c7e485aa9f85c769af4f9a506315206b2f4c553e4b04a8beaf'
m=json.loads(mapfile.read_text());changes={}
for row in m['products']+m['fixtures']:
    source=(lib/row['source']).resolve();dest=(lib/row['target']).resolve()
    assert source.is_relative_to(lib) and dest.is_relative_to(lib)
    assert sha(source)==row['sha256']
    if sha(dest)!=row['sha256']:
        assert sha(dest)==row['previous_sha256']
        changes[row['target']]=row
assert set(changes)=={'include/presonus/dice/sysex.hpp','tests/dice_receiver_lifecycle_bridge.cpp'}
cmake=lib/'CMakeLists.txt';text=cmake.read_text()
anchor='  target_link_libraries(dice_receiver_lifecycle_bridge PRIVATE presonus::cs18_components)'
assert text.count(anchor)==1
replacement=anchor+'\n  target_compile_options(dice_receiver_lifecycle_bridge PRIVATE -fno-lto -fno-devirtualize -fno-devirtualize-speculatively)'
out.mkdir(exist_ok=False)
shutil.copyfile(mapfile,out/'CONTROLLED-APPLY.json')
for name,row in changes.items():
    backup=out/'before'/name;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(lib/name,backup)
    (lib/name).write_bytes((lib/row['source']).read_bytes())
shutil.copyfile(cmake,out/'CMakeLists.before.txt');old=sha(cmake);cmake.write_text(text.replace(anchor,replacement,1))
(out/'validation.json').write_text(json.dumps(dict(applied=True,products=changes,cmake_previous_sha256=old,cmake_current_sha256=sha(cmake),scope='Preserve evidenced virtual post; require actual fixture indirect dispatch; original abstract hierarchy/vtable ABI excluded'),indent=2)+'\n')
print(json.dumps(dict(applied=True,corrected_products=len(changes))))
