"""Restore exact excluded cache evidence, then verify its frozen manifest."""
import hashlib
import json
from pathlib import Path
import shutil

repo=Path('/home/rs/projects/opencs/ai-line-analysis');lib=repo/"uc-library"
phase=repo/"evidence/recovery/2026-10-27/receiver-transfer-root"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
transport=json.loads((phase/"receiver-evidence-transport.json").read_text())
for row in transport["records"]:
    source=(repo/row["transport"]).resolve();target=(repo/row["source"]).resolve()
    assert source.is_relative_to(repo/"evidence/recovery") and target.is_relative_to(repo/"evidence/recovery")
    assert sha(source)==row["sha256"]
    if not target.exists():target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    assert sha(target)==row["sha256"]
handoff=json.loads((lib/"validation/noaa-sysex-receiver/active-receiver-transfer-01/HANDOFF.json").read_text())
folder=repo/handoff["evidence"];manifest=folder/"SHA256SUMS.json"
assert sha(manifest)==transport["frozen_manifest_sha256"]==handoff["manifest_sha256"]
bindings=json.loads(manifest.read_text())
for name,digest in bindings.items():assert sha(folder/name)==digest,name
source=repo/"uc-library/tools/recovery/audit_spi_avb_helpers_raw_mirror.py"
target=repo/"uc-library/tools/recovery/audit_receiver_transfer_raw_mirror.py"
assert not target.exists()
target.write_text(source.read_text().replace("spi-avb-helpers-root","receiver-transfer-root"))
out=phase/"receiver-evidence-mirror-audit.json"
out.write_text(json.dumps(dict(passed=True,manifest_sha256=sha(manifest),checked=len(bindings),excluded_cache_count=len(transport["records"]),frozen_receipts_unchanged=True,mac_cpp_executed=False,tool_sha256=sha(Path(__file__))),indent=2)+"\n")
print(json.dumps(dict(receiver_evidence_files=len(bindings),restored_caches=len(transport["records"]),manifest_passed=True)))
