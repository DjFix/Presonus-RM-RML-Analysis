"""Apply reviewed UART source products without changing frozen evidence."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

repo = Path('/home/rs/projects/opencs/ai-line-analysis')
library = repo / 'uc-library'
candidate = library / 'candidates/dice-uart-assembly'
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
handoff = json.loads((candidate / 'validation/handoff.json').read_text())
proof = candidate / 'validation/replay-02/validation.json'
assert digest(proof) == handoff['proof_sha256']
mapping = {
    'include/presonus/dice/uart_assembly.hpp': 'include/presonus/dice/uart_assembly.hpp',
    'src/Dice3UartAssembly.cpp': 'src/Presonus/DICE/Dice3UartAssembly.cpp',
    'src/UartAssemblyState.cpp': 'src/portable/dice/UartAssemblyState.cpp',
    'src/CclAssemblyCallbacks.cpp': 'src/portable/dice/CclAssemblyCallbacks.cpp',
    'tests/replay.cpp': 'tests/dice_uart_assembly_replay.cpp',
    'tests/source_provider.cpp': 'tests/dice_uart_assembly_source_provider.cpp',
}
# Frozen proof and independent handoff retain the reviewed input identities.
source_hashes = json.loads(proof.read_text())['sources']
for source, target in mapping.items():
    name = 'candidates/dice-uart-assembly/' + source
    assert digest(candidate / source) == source_hashes[name], name
    assert not (library / target).exists(), target
fixtures = {}
for name in ('fixtures.txt', 'arm-output.txt'):
    source = candidate / 'validation/replay-02' / name
    assert digest(source) == handoff['evidence_hashes'][name], name
    target = library / 'validation/dice-uart-assembly' / name
    assert not target.exists(), target
    fixtures[source] = target
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
evidence = repo / 'evidence/recovery/2026-10-27/uart-assembly-application' / stamp
evidence.mkdir(parents=True)
for source, target in mapping.items():
    destination = library / target
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(candidate / source, destination)
for source, target in fixtures.items():
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
records = {target: digest(library / target) for target in mapping.values()}
(evidence / 'application.json').write_text(json.dumps({
    'proof_sha256': digest(proof), 'copied_sources': records,
    'fixtures': {str(p.relative_to(library)): digest(p) for p in fixtures.values()},
    'ready_delta': 0, 'declaration_pending_delta': 1,
}, indent=2) + '\n')
(library / 'validation/format-uart-assembly-paths.json').write_text(
    json.dumps(list(mapping.values()), indent=2) + '\n')
extra = ['CMakeLists.txt', 'cmake/ProductionSourceGroups.cmake',
         'tools/dice_uart_assembly_replay.py',
         *[str(p.relative_to(library)) for p in fixtures.values()]]
(library / 'validation/integration-uart-assembly-additions.json').write_text(
    json.dumps(list(mapping.values()) + extra, indent=2) + '\n')
print(json.dumps({'applied': len(records), 'evidence': str(evidence.relative_to(repo))}))
