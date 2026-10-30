"""Record the admitted Pot/Fader batch without conflating declarations and bodies."""
import hashlib,json,subprocess,sys
from pathlib import Path
assert sys.platform.startswith('linux')
repo=Path.cwd().resolve();lib=repo/'uc-library';phase=repo/'evidence/recovery/2026-10-27/pot-fader-root'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=repo/'uc-library/tools/recovery/count_current_unique.py';target=repo/'uc-library/tools/recovery/count_pot_fader_unique.py'
assert not target.exists();target.write_text(source.read_text().replace('file-transfer-panel-root/unique-current.json','pot-fader-root/unique-current.json'))
subprocess.run([sys.executable,str(target)],check=True)
counter=json.loads((phase/'unique-current.json').read_text())
assert (counter['remaining_unique'],counter['complete_all_roles'],counter['per_elf_ready'],counter['per_elf_pending'])==(9831,342,638,392)
tracker=lib/'validation/embedded-efm/SYMBOLS.md';old=tracker.read_text();assert '## Pot/Fader archive refresh' not in old
tracker.write_text(old+f'''
## Pot/Fader archive refresh — 2026-10-27

Eight retained raw suites freshly pass against the current role archives:
115,933 cases including 88 independent guards. Proof
`evidence/recovery/2026-10-27/pot-fader-root/raw-active-01/validation.json`,
SHA `{sha(phase/'raw-active-01/validation.json')}`. No raw domain change.
Canonical Linux CTest126/126;105 production CPPs compiled once;84 public headers.
''')
subprocess.run([sys.executable,str(lib/'tools/generate_checkpoint.py'),'--library',str(lib),'--repository',str(repo),'--phase','pot-fader','--baseline',str(repo/'temp/recovery-work/checkpoints/2026-10-27-dispatch-transfers.json'),'--output',str(repo/'temp/recovery-work/checkpoints/2026-10-27-pot-fader.md')],check=True)
(phase/'README.md').write_text(f'''# PotControl / FaderControl checkpoint

Canonical Linux126/126 CTest;105 production CPPs compiled once:
72 common,25 CS18,8 RM.84 installed application headers.

638 per-ELF ready /342 distinct names /392 declaration-pending records.
This batch adds15 unique original names: eight lifecycle names bounded-ready
(16 per-ELF entries), seven ordinary names declaration-pending (14 entries).
Actual C1/C2 and D1/D0 native lifecycle observations support only the documented
domains; original D2 symbols are absent and no original D2 rows are invented.
Original namespaces are Presonus::Panel::PotControl and FaderControl.

28,960 retained original/native cases freshly pass in Release and sanitizers.
Real CCL parameters, observer removal, timer cleanup and actual deallocation are
checked; unsupported concurrency, arbitrary callbacks, original ARM object ABI,
startup and physical hardware remain unverified. Ordinary return declarations
remain unresolved. No original Core bodies are reconstructed or executed.

Existing six ready/ten pending SPI CMake bindings refreshed; all prior entries
retained. Raw MCU115,933-case domain separately replayed; no ELF identity claim.
Remaining unique host names: {counter['remaining_unique']}, outside Core
{counter['manual_remaining']}, CCL source route {counter['core_source_route_remaining']}.
Manual buckets: `{json.dumps(counter['manual_buckets'],sort_keys=True)}`.

Full proof/logs and source snapshots are retained in this phase directory;
uc-library/SYMBOLS.md and the project-temp compact checkpoint track the ledger.
''')
print(json.dumps(dict(ready=638,names=342,pending=392,remaining=9831)))
