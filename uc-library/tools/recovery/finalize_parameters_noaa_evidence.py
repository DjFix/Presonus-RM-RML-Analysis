"""Preserve the completed NOAA replay and its mandatory combined preflight."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path('/home/rs/projects/opencs/ai-line-analysis')
LIB = ROOT/"uc-library"
PHASE = ROOT/"evidence/recovery/2026-10-27/efm-parameters-input-pin-root"
WORK = ROOT/"temp/noaa-spi-refresh-params/parameters-input-pin-01"
TARGET = LIB/"validation/noaa-spi-packets-refresh/parameters-input-pin-01"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
preflight = json.loads((PHASE/"combined-preflight.json").read_text())
admission = json.loads((PHASE/"combined-admission.json").read_text())
assert preflight["validated_only"]
for result in (preflight, admission):
    assert (result["portable_ready_entries"], result["unique_mangled_methods"], result["compiled_declaration_pending_entries"]) == (587,314,296)
    assert not any(result[key] for key in ("stale_previous_entries", "demoted_entries", "promoted_pending_entries"))
keys = lambda rows: {(r["original_elf_sha256"], r["mangled"]) for r in rows}
old_ready = json.loads((PHASE/"before/validation/ready-functions.json").read_text())["functions"]
old_pending = json.loads((PHASE/"before/validation/compiled-functions.json").read_text())["functions"]
ready = json.loads((LIB/"validation/ready-functions.json").read_text())["functions"]
pending = json.loads((LIB/"validation/compiled-functions.json").read_text())["functions"]
pin = json.loads((LIB/"validation/panel-input-pin-lifetime/ready-functions.fragment.json").read_text())["functions"]
assert len(pin) == 10
assert keys(ready) == keys(old_ready) | keys(pin)
assert keys(pending) == keys(old_pending)
assert keys(ready).isdisjoint(keys(pending))
commands = json.loads((WORK/"commands.json").read_text())
assert commands and all(row["returncode"] == 0 for row in commands)
proof = json.loads((TARGET/"validation.json").read_text())
assert all(sha(LIB/name) == digest for name,digest in proof["sources"].items())
assert all(sha(ROOT/name) == digest for name,digest in proof["repository_sources"].items())
shutil.copytree(WORK/"logs", TARGET/"logs")
shutil.copyfile(WORK/"commands.json", TARGET/"commands.json")
journal = {
    "passed": True,
    "scope": "Existing NOAA native replay completed; standalone cardinality assertion rejected the six companion InputPin pending records. Admission used the standard combined readiness merger with both active fragments, without repeating completed native/original replays.",
    "combined_preflight_sha256": sha(PHASE/"combined-preflight.json"),
    "combined_admission_sha256": sha(PHASE/"combined-admission.json"),
    "ready_identity_delta": 10, "pending_identities_preserved": len(pending),
    "ready_pending_disjoint": True,
    "noaa_proof_sha256": sha(TARGET/"validation.json"),
    "noaa_pending_proof_sha256": sha(TARGET/"pending-validation.json"),
    "native_command_log_sha256": sha(TARGET/"commands.json"),
    "commands_succeeded": len(commands),
    "logs": {p.name:sha(p) for p in (TARGET/"logs").iterdir() if p.is_file()},
    "tool_sha256": sha(Path(__file__)),
}
(TARGET/"combined-finalization.json").write_text(json.dumps(journal,indent=2)+"\n")
(PHASE/"combined-finalization.json").write_text(json.dumps(journal,indent=2)+"\n")
evidence = ROOT/"evidence/recovery/2026-10-27/noaa-spi-refresh-params-active/parameters-input-pin-01"
shutil.copytree(TARGET, evidence)
for name in proof["sources"]:
    dest = evidence/"source"/name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(LIB/name, dest)
print(json.dumps({"passed":True,"ready":len(ready),"pending":len(pending),"ready_added":10,"commands_preserved":len(commands)}))
