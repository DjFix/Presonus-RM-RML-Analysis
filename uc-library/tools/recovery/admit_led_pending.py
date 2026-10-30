"""Preserve worker proofs while admitting unresolved LED returns as pending."""
import hashlib
import json
from pathlib import Path

repo=Path('/home/rs/projects/opencs/ai-line-analysis')
lib=repo/'uc-library'
fragment=lib/'validation/panel-led-state/replay-01/readiness-records.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(fragment)=='ba026e3fd3b04dcca64ad6fe221272595d7ee95cb6fecf726836e874e5a394d5'
rows=json.loads(fragment.read_text())['functions']
assert len(rows)==10
pending=[]
for row in rows:
    proof=lib/row['validation']
    assert sha(proof)==row['validation_sha256']
    data=json.loads(proof.read_text())
    assert data['compiled_mangled_names_matched'] and data['cpp_differential_passed']
    pending.append(dict(row,portable_ready=False,cpp_compiled=True,
        mangling_namespace_checked=True,original_return_declaration_proven=False,
        admission_reason='Original return declarations unresolved; original R0 ignored in state/dispatch proof. Keep compiled/declaration-pending.'))
target=lib/'validation/panel-led-state/compiled-functions.admitted.fragment.json'
target.write_text(json.dumps(dict(functions=pending),indent=2)+'\n')
print(json.dumps(dict(compiled_pending_entries=len(pending),fragment_sha256=sha(target))))
