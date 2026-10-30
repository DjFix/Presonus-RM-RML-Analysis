"""Transport the helper-excluded generated cache without changing frozen receipts."""
import hashlib
import json
from pathlib import Path
import shutil

repo=Path.cwd().resolve();lib=repo/"uc-library"
phase=repo/"evidence/recovery/2026-10-27/receiver-transfer-root"
handoff=json.loads((lib/"validation/noaa-sysex-receiver/active-receiver-transfer-01/HANDOFF.json").read_text())
folder=(repo/handoff["evidence"]).resolve();assert folder.is_relative_to(repo/"evidence/recovery")
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
records=[]
for index,source in enumerate(sorted(folder.rglob("CMakeCache.txt"))):
    target=folder/"supplemental-transport"/(str(index)+".snapshot.txt")
    assert not target.exists();target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source,target);assert sha(source)==sha(target)
    records.append(dict(source=str(source.relative_to(repo)),transport=str(target.relative_to(repo)),sha256=sha(source)))
output=phase/"receiver-evidence-transport.json";assert not output.exists()
output.write_text(json.dumps(dict(records=records,frozen_manifest_sha256=sha(folder/"SHA256SUMS.json"),frozen_receipts_unchanged=True),indent=2)+"\n")
print(json.dumps(dict(cache_snapshots=len(records),evidence=handoff["evidence"])))
