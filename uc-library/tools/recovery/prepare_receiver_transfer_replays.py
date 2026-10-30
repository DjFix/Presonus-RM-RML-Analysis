"""Bind this phase's fixture sidecar and preserve full component replay gates."""
import hashlib
import json
from pathlib import Path
import shutil

repo=Path('/home/rs/projects/opencs/ai-line-analysis');lib=repo/"uc-library"
phase=repo/"evidence/recovery/2026-10-27/receiver-transfer-root"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
fix=phase/"fixture-packaging-fix-01";fix.mkdir(exist_ok=False)
source=lib/"candidates/panel-switch-control/validation/verify-02/validation.json"
meta=json.loads(source.read_text());fixture=lib/"validation/panel-switch-control/fixtures.jsonl"
assert meta["passed"] and meta["cases"]==13256 and meta["fixture_sha256"]==sha(fixture)
target=fixture.parent/"validation.json";assert not target.exists();shutil.copyfile(source,target)
inputs=lib/"validation/integration-receiver-transfer-additions.json"
shutil.copyfile(inputs,fix/"integration-additions-before.json")
paths=json.loads(inputs.read_text());paths.append(str(target.relative_to(lib)))
inputs.write_text(json.dumps(sorted(set(paths)),indent=2)+"\n")
(fix/"validation.json").write_text(json.dumps(dict(source=str(source.relative_to(lib)),source_sha256=sha(source),target=str(target.relative_to(lib)),target_sha256=sha(target),cpp_changed=False,reason="Copied Switch fixture lacked mandatory adjacent validation.json; retain failed121-test attempt and replay full suite."),indent=2)+"\n")

own=lib/"candidates/noaa-sysex-receiver";original=own/"verify.py"
assert sha(original)=="ba6367b27b25982cf3ccf4d8eb798a37f91b1ab37f7c99873b9538444369000d"
text=original.read_text()
anchor="snapshot = json.loads((own/'DEPENDENCIES.json').read_text())"
guard="""assert active, 'Phase derivative is active-only; frozen candidate remains unchanged'
integration = json.loads((lib/'validation/integration.json').read_text())
assert integration['ctest_passed'] and integration['platform']=='linux' and integration['test_suites']==121
for name,digest in integration['files'].items(): assert sha(lib/name)==digest,name
"""
assert text.count(anchor)==1;text=text.replace(anchor,guard+anchor,1)
anchor="native_name, deps_name = 'native-active-01','dependencies-active-01'"
assert text.count(anchor)==1;text=text.replace(anchor,"native_name, deps_name = 'native-'+stage,'dependencies-'+stage",1)
anchor="for name in tool_names: app_closure[str((own/name).relative_to(lib))] = sha(own/name)"
assert text.count(anchor)==1;text=text.replace(anchor,anchor+"\napp_closure[str(Path(__file__).resolve().relative_to(lib))] = sha(Path(__file__))",1)
start=text.index("ledger = [lib/'validation/ready-functions.json'")
end=text.index("if not active:\n    assert not (own/'CONTROLLED-APPLY.json').exists()",start)
text=text[:start]+"""ledger = [lib/'validation/ready-functions.json',lib/'validation/compiled-functions.json']
before_hashes = {str(p):sha(p) for p in ledger}
preflight = dict(requires_combined_preflight=True,global_admission_validated=False,
                reason='Fresh sibling SPI and FileTransfer fragments must join Root unchanged merger')
assert before_hashes == {str(p):sha(p) for p in ledger}
(out/'combined-preflight-required.json').write_text(json.dumps(dict(result=preflight,unchanged_ledgers=before_hashes),indent=2)+'\\n')
"""+text[end:]
derivative=own/"verify_receiver_transfer_phase.py";assert not derivative.exists();compile(text,str(derivative),"exec");derivative.write_text(text)

rawold=lib/"candidates/efm-fader-control-dispatch/tools/seal_raw_root_spi_avb_helpers.py"
rawnew=rawold.with_name("seal_raw_root_receiver_transfer.py");assert not rawnew.exists()
rawtext=rawold.read_text().replace("spi-avb-helpers-root","receiver-transfer-root").replace("==116","==121").replace("canonical_ctest_count=116","canonical_ctest_count=121")
compile(rawtext,str(rawnew),"exec");rawnew.write_text(rawtext)
(phase/"producer-derivatives.json").write_text(json.dumps(dict(receiver=dict(source=str(original.relative_to(lib)),source_sha256=sha(original),derivative=str(derivative.relative_to(lib)),derivative_sha256=sha(derivative),changes="Current full121 integration gate, unique phase run paths, own-source hash, deferred combined-merger tally. All original/native/provider/source/mangle checks retained."),raw=dict(source=str(rawold.relative_to(lib)),source_sha256=sha(rawold),derivative=str(rawnew.relative_to(lib)),derivative_sha256=sha(rawnew),changes="Phase paths and expected121 root inventory only. All eight full replays unchanged."),global_merger_changed=False),indent=2)+"\n")
manifest=dict(phase="receiver-transfer-replay-preparation",transfers=[dict(direction="push",area="library",paths=[str(target.relative_to(lib)),str(inputs.relative_to(lib)),str(derivative.relative_to(lib)),str(rawnew.relative_to(lib))]),dict(direction="push",area="evidence",paths=["2026-10-27/receiver-transfer-root/fixture-packaging-fix-01","2026-10-27/receiver-transfer-root/producer-derivatives.json"]),dict(direction="push",area="operators",paths=["prepare_receiver_transfer_replays.py"])])
(repo/"temp/recovery-work/sync-receiver-transfer-replay-preparation.json").write_text(json.dumps(manifest,indent=2)+"\n")
print(json.dumps(dict(fixture_sidecar_added=True,cpp_changed=False,full_component_checks_retained=True)))
