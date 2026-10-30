"""Check local mirror metadata against the completed Linux CCL integration."""
import hashlib
import json
from pathlib import Path

repo = Path('/home/rs/projects/opencs/ai-line-analysis')
lib = repo / 'uc-library'
cache = {}
def sha(path):
    if path not in cache:
        cache[path] = hashlib.sha256(path.read_bytes()).hexdigest()
    return cache[path]
def read(name):
    return json.loads((lib / name).read_text())
integration = read('validation/integration.json')
assert integration == read('validation/integration-linux.json')
assert integration['platform'] == 'linux' and integration['ctest_passed'] and integration['test_suites'] == 44
for name, digest in integration['files'].items():
    assert sha(lib / name) == digest, name
assert sha(repo / integration['test_log']) == integration['test_log_sha256']
for name, digest in integration['logs'].items():
    assert sha(repo / name) == digest, name
ready = read('validation/ready-functions.json')['functions']
pending = read('validation/compiled-functions.json')['functions']
assert len(ready) == 407 and len(pending) == 41
assert len({r['mangled'] for r in ready}) == 213
for record in ready + pending:
    assert sha(lib / record['validation']) == record['validation_sha256'], record['mangled']
    for name, digest in record['sources'].items():
        assert sha(lib / name) == digest, name
    if record.get('portable_ready'):
        assert isinstance(record.get('domain'), str) and record['domain'].strip()
coverage = read('tracking/coverage.json')['roles']
assert sum(role['summary']['portable_reconstructions_ready'] for role in coverage.values()) == 407
assert sum(role['summary']['compiled_declaration_pending_entries'] for role in coverage.values()) == 41
report = dict(passed=True, canonical_platform='linux', ctest_suites=44,
              integrated_inputs=len(integration['files']), ready_elf_entries=407,
              distinct_ready_mangles=213, declaration_pending_entries=41,
              integration_sha256=sha(lib/'validation/integration.json'),
              ready_ledger_sha256=sha(lib/'validation/ready-functions.json'),
              pending_ledger_sha256=sha(lib/'validation/compiled-functions.json'),
              symbol_table_sha256=sha(lib/'SYMBOLS.md'),
              original_arm_abi_verified=False, hardware_verified=False,
              scope='Local mirror hashes and source-bound Linux proof metadata; no local C++ build')
out = repo/'evidence/recovery/2026-10-27/avb-ccl-root/local-mirror-audit.json'
out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
