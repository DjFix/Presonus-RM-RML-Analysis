"""Freeze this fixed Fader/SPI admission input set without changing ledgers."""
import hashlib
import json
from pathlib import Path
import re
import shlex

repo = Path.cwd().resolve()
lib = repo / 'uc-library'
out = repo / 'evidence/recovery/2026-10-28/onoff-batch'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
ready = ['candidates/dsp-gate-parameter-list/validation/onoff-active-01/ready.fragment.json', 'validation/noaa-spi-service-onoff/root-closure-01/ready-functions.fragment.json']
pending = ['candidates/dsp-gate-parameter-list/validation/onoff-active-01/pending.fragment.json', 'validation/noaa-spi-service-onoff/root-closure-01/pending-functions.fragment.json']
sources = {}
totals = []
for names in (ready, pending):
    count = 0
    for name in names:
        for row in read(lib / name)['functions']:
            count += 1
            assert row['domain'].strip()
            proof = lib / row['validation']
            assert sha(proof) == row['validation_sha256']
            validation = read(proof)
            assert validation['cpp_differential_passed']
            assert validation['compiled_mangled_names_matched']
            assert validation.get('passed', True)
            for source, digest in row['sources'].items():
                assert sha(lib / source) == digest, source
                assert source not in sources or sources[source] == digest
                sources[source] = digest
            for source, digest in row.get('repository_sources', {}).items():
                assert sha(repo / source) == digest, source
    totals.append(count)
assert totals == [14, 14], totals
commands_path = repo / 'temp/core-upstream/root-integration-01/compile_commands.json'
tests = {}
for test in ['tests/uc_onoff_formatter_tests.cpp']:
    commands = [row for row in read(commands_path) if Path(row['file']).resolve() == lib / test]
    assert len(commands) == 1
    command = commands[0]
    tokens = command.get('arguments') or shlex.split(command['command'])
    flags = [t for t in tokens if re.match(r'-[DU]NDEBUG(?:=|$)', t)]
    assert flags and flags[-1] == '-UNDEBUG', flags
    tests[test] = dict(command=command, ndebug_flags=flags, source_sha256=sha(lib / test))
assert read(lib / 'validation/integration.json')['test_suites'] == 224
assert read(lib / 'validation/formatting.json')['format_check_passed']
assertions = dict(passed=True, tests=tests, compile_commands_sha256=sha(commands_path))
(out / 'assertions.json').write_text(json.dumps(assertions, indent=2) + '\n')
cpp_paths = sorted(p for p in sources if Path(p).suffix in ('.cpp', '.hpp', '.h'))
manifest = dict(passed=True, ready=ready, pending=pending,
                fragment_hashes={p: sha(lib / p) for p in ready + pending},
                source_hashes=sources, source_count=len(sources), cpp_paths=cpp_paths,
                ready_entries=14, pending_entries=14)
(out / 'FINAL-FRAGMENTS.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps(dict(passed=True, ready=14, pending=14, sources=len(sources), cpp_paths=len(cpp_paths))))
