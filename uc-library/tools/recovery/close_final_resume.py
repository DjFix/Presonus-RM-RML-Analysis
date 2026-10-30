"""Record the user-requested safe pause after final batch admission."""
from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone

root = Path(__file__).resolve().parents[3]
evidence = root / 'evidence/recovery/2026-10-28/final-resume-batch'
control = root / 'temp/recovery-work'
raw = evidence / 'raw-active-01/validation.json'
proof = json.loads(raw.read_text())
assert proof['passed'] and proof['cases'] == 115933
role = json.loads((evidence / 'role-audit-02.log').read_text())
assert role['passed'] and role['units'] == 112
counts = json.loads((evidence / 'unique-current.json').read_text())
assert (counts['per_elf_ready'], counts['per_elf_pending']) == (637, 422)
digest = hashlib.sha256(raw.read_bytes()).hexdigest()
tracker = root / 'uc-library/validation/embedded-efm/SYMBOLS.md'
marker = '## Final resume archive refresh — 2026-10-28 UTC'
assert marker not in tracker.read_text()
with tracker.open('a') as stream:
    stream.write(f'\n{marker}\n\nEight retained raw suites passed: 115,933 cases, including 88 independent guards.\nProof: `evidence/recovery/2026-10-28/final-resume-batch/raw-active-01/validation.json`\nSHA-256: `{digest}`. No raw code/domain change.\nCanonical Linux CTest 136/136; 112 production CPPs compiled once; 88 application headers.\n')
checkpoint = control / 'checkpoints/2026-10-28-safe-pause-final-resume.md'
assert not checkpoint.exists()
checkpoint.write_text('''# Safe pause — final resume batch

All three agents completed; their results were integrated and admitted. No new batch is authorized by this checkpoint.

- Reconstructed 13 ordinary method names: DICE 5, Network 4, Biquad 4. Their original return declarations remain pending.
- Canonical ledger: 637 ready per-ELF records / 341 distinct names; 422 declaration-pending records. Two routing records explicitly demoted using guarded manifests; no silent removals.
- Remaining to readiness: 9,832 distinct names, including 7,048 non-Core names without admitted reconstruction, 243 declaration-pending names, and 2,541 upstream Core source-route names.
- Linux: 136/136 CTest; formatter 23.1.3; 88 public headers; 112 production CPPs compiled once (75 common / 27 CS18 / 10 RM). Installed archive and relocated consumer audit passed.
- Retained raw MCU evidence: eight suites / 115,933 cases; separate from host ELF counts.
- Full evidence: evidence/recovery/2026-10-28/final-resume-batch/. Canonical tracker: uc-library/SYMBOLS.md.
- Readiness/source hash audit passed 976 checks: evidence/recovery/2026-10-27/final-resume-close-20261028/local-mirror-audit.json.
- First role audit failed its blanket RTTI assertion. Scoped replay requires exactly the two existing DICE no-RTTI exceptions; all other checks retained. Both logs preserved.
- Active worker checkpoints: candidates/dice-next-services/ACTIVE-CHECKPOINT.md; candidates/uc-network-manager-next-services/ACTIVE-CHECKPOINT.md; candidates/dsp-biquad-methods/CHECKPOINT.md (all under uc-library/).
- Future work: five Biquad incremental methods; DICE lifecycle and unresolved declarations; Network lifecycle/listeners/registrar; remaining tracked mixer/surface functions. Preserve original namespaces and mangling, Core source policy, and existing admission gates.
- No active worker or validation jobs remain. No hardware/flash tests, Mac synchronization, commits or pushes performed.
- User requested a pause below 50% remaining allowance and explicitly authorized finishing integration before stopping. Allowance telemetry was unavailable; this pause records the explicit safe-stop boundary, not an observed quota percentage.
''')
prior = control / 'PAUSE.json'
(evidence / 'pause-control-before.json').write_bytes(prior.read_bytes())
state = dict(state='paused', paused_at=datetime.now(timezone.utc).isoformat(), user_authorized=True,
             reason='User-requested safe pause after integrating current agents',
             checkpoint=str(checkpoint.relative_to(root)), active_jobs=[], allowance_remaining_percent=None)
prior.write_text(json.dumps(state, indent=2) + '\n')
next_file = control / 'NEXT.md'
if next_file.exists():
    (evidence / 'next-before.md').write_bytes(next_file.read_bytes())
next_file.write_text(f'Paused. Read `{checkpoint.relative_to(root)}` and wait for explicit resume authorization.\n')
print(json.dumps(state))
