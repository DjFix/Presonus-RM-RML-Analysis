"""Read-only source/receipt hash checks; does not replay or execute firmware."""
import hashlib
import json
from pathlib import Path

ROOT = Path('/home/rs/projects/opencs/ai-line-analysis')
LIB = ROOT / "uc-library"
EVIDENCE = ROOT / "evidence/recovery/2026-10-27/efm-reconstruction"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local_path(name):
    if name.startswith("uc-library/"):
        return LIB / name.removeprefix("uc-library/")
    return ROOT / name


baseline = json.loads((ROOT / "temp/recovery-work/checkpoints/2026-10-27-control-file-services.json").read_text())
checks = {}
for name, expected in baseline["inputs"].items():
    assert digest(local_path(name)) == expected, name
    checks[name] = expected

audit_path = EVIDENCE / "fader/audit-linux-01/validation.json"
assert digest(audit_path) == "84a047e6dae1f28b4829c54b9bb80992cd36d6bed9a3f58032c99861ef031f93"
audit = json.loads(audit_path.read_text())
assert audit["passed"] and audit["native_namespace_check"]
for name, expected in audit["hashes"].items():
    assert digest(local_path(name)) == expected, name
    checks[name] = expected

panel_path = EVIDENCE / "panel/protocol-static-05/receipt.json"
assert digest(panel_path) == "fb2b256b02072d19d73d6753c3ba41289aa6c5112e14eea0857a756924538b72"
panel = json.loads(panel_path.read_text())
image_path = ROOT / "evidence/recovery/2026-10-27/efm32-faders/panel_surface_code.bin"
assert digest(image_path) == panel["image_sha256"]
image = image_path.read_bytes()
ranges = []
for row in panel["functions"]:
    offset, size = row["file_offset"], row["size"]
    assert offset >= 0 and offset + size <= len(image)
    assert row["canonical_thumb_address"] - row["analysis_base"] == offset
    assert row["range_end_exclusive"] == row["canonical_thumb_address"] + size
    assert hashlib.sha256(image[offset:offset + size]).hexdigest() == row["range_sha256"]
    ranges.append({key: row[key] for key in ("analysis_name", "canonical_thumb_address", "file_offset", "size", "range_sha256")})

result = {
    "passed": True,
    "scope": "Mac read-only mirror hashes, admitted baseline hashes and raw panel ranges; no fixture replay, compilation, semantic or hardware validation",
    "baseline_counts": {key: baseline[key] for key in ("ready_entries", "ready_distinct_mangles", "declaration_pending_entries", "test_suites")},
    "checked_file_count": len(checks),
    "hashes": checks,
    "fader_audit_sha256": digest(audit_path),
    "panel_receipt_sha256": digest(panel_path),
    "panel_image_sha256": digest(image_path),
    "panel_ranges": ranges,
    "tool_sha256": digest(Path(__file__)),
    "firmware_executed": False,
    "hardware_accessed": False,
}
out = EVIDENCE / "cross-layer/resume-mirror-audit.json"
with out.open("x") as stream:
    stream.write(json.dumps(result, indent=2) + "\n")
print(json.dumps({"passed": True, "checked_files": len(checks), "panel_ranges": len(ranges), "baseline_counts": result["baseline_counts"], "output": str(out.relative_to(ROOT))}))
