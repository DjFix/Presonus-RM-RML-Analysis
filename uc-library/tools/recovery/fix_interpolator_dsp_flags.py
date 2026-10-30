"""Preserve Dsp.cpp options after the later float-options replacement."""
import hashlib
import json
from pathlib import Path

repo = Path.cwd().resolve()
lib = repo / "uc-library"
out = repo / "evidence/recovery/2026-10-28/interpolator-programmer-batch/dsp-flags-fix-01"
out.mkdir(parents=True, exist_ok=False)
path = lib / "CMakeLists.txt"
before = path.read_bytes()
text = before.decode()
line = 'set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/mixer_dsp/Dsp.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin)'
marker = 'set_source_files_properties(src/mixer_dsp/Dsp.cpp src/mixer_dsp/FilterControllers.cpp PROPERTIES\n  COMPILE_OPTIONS "${PRESONUS_DSP_FLOAT_OPTIONS}")'
assert text.count(line) == text.count(marker) == 1
assert text.index(line) < text.index(marker)
updated = text.replace(line + "\n", "", 1).replace(marker, marker + "\n" + line, 1)
assert updated.index(line) > updated.index(marker)
(out / "CMakeLists.before.txt").write_bytes(before)
path.write_text(updated)
(out / "CMakeLists.after.txt").write_bytes(path.read_bytes())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
proof = dict(passed=True, scope="Only relocate the existing Dsp-specific append after its overwriting assignment.",
             previous_sha256=hashlib.sha256(before).hexdigest(), current_sha256=sha(path),
             tool_sha256=sha(Path(__file__)), guards_released_before_mutation=True,
             fresh_build_tests_and_active_proofs_required=True)
(out / "application.json").write_text(json.dumps(proof, indent=2) + "\n")
source = lib / "validation/integration-interpolator-programmer-additions.json"
additions = sorted(set(json.loads(source.read_text())) | {str(Path(__file__).relative_to(lib))})
(lib / "validation/integration-interpolator-programmer-flags-additions.json").write_text(json.dumps(additions, indent=2) + "\n")
print(json.dumps(proof))
