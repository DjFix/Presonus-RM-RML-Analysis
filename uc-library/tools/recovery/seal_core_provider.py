"""Record completed source-provider integration separately from ELF readiness."""
import hashlib
import json
from pathlib import Path

repo = Path('/home/rs/projects/opencs/ai-line-analysis')
lib = repo / 'uc-library'
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
phase = repo / 'evidence/recovery/2026-10-27/core-provider-root/linux'
integration = json.loads((phase / 'validation.json').read_text())
audit = json.loads((phase / 'install-audit.json').read_text())
consumer_path = lib / 'candidates/core-root-consumer/validation/validation.json'
assert sha(consumer_path) == 'dc5daa5a3143f91d42b9b5391eefa615f3e111a280e9db1b78d7d8b311355b74'
consumer = json.loads(consumer_path.read_text())
assert integration['platform'] == 'linux' and integration['ctest_passed']
assert integration['test_suites'] == 39 and audit['compiled_mangles_matched']
assert audit['header_set_matches'] and audit['provider_sdk_matches']
assert audit['application_header_count'] == 40 and audit['provider_header_count'] == 248
assert consumer['passed'] and consumer['real_core_source_used'] and consumer['app_rtti_enabled']
assert len(consumer['sdk_header_hashes']) == 248
for path, digest in integration['logs'].items():
    assert sha(repo / path) == digest
proofs = [phase / 'validation.json', phase / 'install-audit.json', consumer_path]
report = dict(passed=True, platform='linux', source_commit=consumer['source_commit'],
              original_core_binary_reconstructed=False, original_arm_abi_verified=False,
              hardware_verified=False, source_provider_ctest_suites=39,
              application_header_count=40, provider_header_count=248,
              installed_original_application_mangles=len(audit['ready_original_mangles']),
              relocated_package_consumer_passed=True,
              evidence={str(p.relative_to(repo)): sha(p) for p in proofs},
              provider_sdk_hashes=audit['provider_sdk_hashes'],
              scope='Source-built CCL provider and relocatable public package; application bindings tracked in later source-bound proofs. No original Core ELF readiness promotion.')
out = lib / 'validation/core-upstream/root-provider-validation.json'
out.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'proof': str(out.relative_to(repo)), 'sha256': sha(out), 'passed': True}))
