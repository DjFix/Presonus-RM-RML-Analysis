"""Create narrowly scoped producer derivatives; require separate combined admission."""
import hashlib
import json
from pathlib import Path

repo = Path('/home/rs/projects/opencs/ai-line-analysis')
lib = repo / "uc-library"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
changes = []

original = lib / "candidates/panel-led-control-lifecycle/active_reseal.py"
assert sha(original) == "c257be28cdb7fffee488753975cd32a345fa905fa01607934c44a14e8b59d26f"
text = original.read_text()
start = text.index("preflight=run('actual-merger-dry-run'")
text = text[:start] + '''assert ledger_state()==before
for product in mapping['products']:assert sha(lib/product['target'])==product['sha256']
(out/'producer-result.json').write_text(json.dumps(dict(status='proofs produced; combined root preflight required; not admitted',ready_entries=8,pending_entries=24,legacy_cases=31504,new_cases=32916,proof_sha256=sha(proofpath),ready=str(readyfile.relative_to(lib)),pending=str(pendingfile.relative_to(lib)),ready_sha256=sha(readyfile),pending_sha256=sha(pendingfile),ledgers_history_unchanged=True,active_products_unchanged=True,original_oracle_regenerated=False),indent=2)+'\\n')
print((out/'producer-result.json').read_text(),end='')
'''
target = original.with_name("active_reseal_led_server_control.py")
assert not target.exists()
compile(text, str(target), "exec")
target.write_text(text)
changes.append(dict(source=str(original.relative_to(lib)), source_sha256=sha(original), derivative=str(target.relative_to(lib)), derivative_sha256=sha(target), change="Retain all active behavioral/source checks; replace final standalone tally with explicit pending combined-preflight artifact. No admission."))

original = lib / "candidates/noaa-spi-refresh-led-server-control/tools/replay_existing.py"
text = original.read_text()
start = text.index("    argv=[sys.executable,lib/'tools/merge_readiness.py'")
end = text.index("    assert set(previous_sources)<=set(sources)", start)
text = text[:start] + "    result=dict(status='proofs produced; combined root preflight required; not admitted')\n" + text[end:]
text = text.replace("write(target/'readiness-preflight.json',dict(passed=True,result=result,", "write(target/'producer-result.json',dict(passed=False,requires_combined_preflight=True,result=result,")
target = original.with_name("produce_existing.py")
assert not target.exists()
compile(text, str(target), "exec")
target.write_text(text)
changes.append(dict(source=str(original.relative_to(lib)), source_sha256=sha(original), derivative=str(target.relative_to(lib)), derivative_sha256=sha(target), change="Retain full five-identity replay, source closure, objects, real providers and ledger guards; defer standalone tally into combined root preflight. No admission."))
output = repo / "evidence/recovery/2026-10-27/led-server-control-root/producer-derivatives.json"
assert not output.exists()
output.write_text(json.dumps(dict(derivatives=changes, combined_preflight_required=True, global_merger_modified=False), indent=2) + "\n")
print(json.dumps({"derivatives":len(changes), "admitted":False}))
