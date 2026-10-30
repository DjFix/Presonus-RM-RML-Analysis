"""Record a stopped attempt without calling the original function unrecoverable."""
import hashlib
import json
from pathlib import Path

repo=Path('/home/rs/projects/opencs/ai-line-analysis')
lib=repo/'uc-library'
manifest=json.loads((lib/'recovered-all/client/manifest.json').read_text())
symbols=json.loads((lib/'recovered-all/client/symbols.json').read_text())
rows=[row for row in symbols if row.get('address')==0xccf88 and row.get('kind')=='STT_FUNC']
assert len(rows)==1 and 'assembleSYSEX' in rows[0]['demangled']
row=rows[0]
report=dict(function=row,role='client',original_elf_sha256=manifest['sha256'],
            status='Unreconstructed; this worker attempt stopped',
            reason='Analysis worker returned an automatic cybersecurity classification before completing this candidate.',
            reconstruction_proven_impossible=False,portable_ready=False,
            existing_evidence='Verified ELF bytes and existing unvalidated static pseudocode remain available.',
            next_approach='Review existing static exports and bounded offline protocol fixtures; retain exact identity and log any remaining unsupported cases.',
            physical_device_accessed=False)
out=repo/'evidence/recovery/2026-10-27/recovery-gaps/uart-assembly-worker-stop.json'
out.parent.mkdir(parents=True,exist_ok=True)
if out.exists():
    assert json.loads(out.read_text())==report,'Preserve an existing different attempt record'
else:
    out.write_text(json.dumps(report,indent=2)+'\n')
index=lib/'validation/RECOVERY-GAPS.md'
assert not index.exists(),'Do not overwrite an existing recovery gap index'
index.write_text('# Unresolved reconstruction attempts\n\n'
    'A stopped tool attempt is not proof that its function cannot be recovered. '
    'Pending functions remain in the symbol tables and are not marked ready.\n\n'
    '| Binary | Original symbol | Status | Reason / next approach |\n'
    '|---|---|---|---|\n'
    f'| CS18AI 13840 | `{row["mangled"]}` | Unreconstructed | Worker stopped on automatic classification; use existing static exports and bounded offline fixtures. |\n\n'
    'Exact original identity and the attempt record are preserved in project '
    '`evidence/recovery/2026-10-27/recovery-gaps/uart-assembly-worker-stop.json`. '
    'No impossibility or semantic-equivalence claim is made.\n')
print(json.dumps(dict(record=str(out.relative_to(repo)),mangled=row['mangled'],
                      record_sha256=hashlib.sha256(out.read_bytes()).hexdigest())))
