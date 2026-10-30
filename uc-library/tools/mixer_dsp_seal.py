#!/usr/bin/env python3
"""Seal bounded DSP validation records; never modifies the global readiness ledger."""
import argparse
import hashlib
import json
from pathlib import Path

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repository', type=Path)
    args = parser.parse_args()
    root = args.repository.resolve()
    library = root/'temp/recovery-package/uc-library'
    evidence = root/'evidence/recovery/2026-10-26/mixer-dsp'
    out = library/'validation/mixer-dsp'
    files = ['include/presonus/mixer_dsp/Dsp.hpp',
             'src/mixer_dsp/Dsp.cpp', 'tests/mixer_dsp_tests.cpp',
             'tools/mixer_dsp_oracle.py', 'tools/mixer_dsp_seal.py']
    sources = {name: digest(library/name) for name in files}
    log = (evidence/'final-format-replay.log').read_text()
    formatting = json.loads((library/'validation/formatting.json').read_text())
    assert formatting['format_check_passed']
    for name in files[:3]:
        assert formatting['files'][name] == sources[name]
    formatter = dict(version=formatting['formatter'], reference='validation/formatting.json',
                     sha256=digest(library/'validation/formatting.json'))
    assert 'PASS: E=4 G=1018 M=1008 N=13104 R=13104 S=630' in log
    assert 'PASS: M=1008 N=13104 R=13104 S=630' in log
    domain = ('Bounded fixture cases only: IEEE binary32 FE_TONEAREST, gradual '
              'underflow, FTZ/DAZ disabled (test preflight), -fno-fast-math '
              '-ffp-contract=off. Portable nine-float state with valid, '
              'nonoverlapping storage. Exact return bits and unchanged 36-byte '
              'state compared with original ARM code and original soft-float '
              'helpers in Unicorn. Floating exception flags, ARM object/vtable '
              'ABI compatibility and hardware interoperability are unproven.')
    records = []
    pending = []
    for role, directory in [('server', out), ('client', out/'client')]:
        report = json.loads((directory/'arm-oracle.json').read_text())
        vectors = directory/'arm-vectors.txt'
        assert digest(vectors) == report['vectors_sha256']
        for op, symbol in report['functions'].items():
            assert symbol['mangled'] in log
            record = dict(symbol, role=role,
                          firmware_version=13731 if role=='server' else 13840,
                          original_elf_sha256=report['original_elf_sha256'],
                          sources=sources, domain=domain, formatting=formatter,
                          cpp_compiled=True, mangling_namespace_checked=True,
                          arm_differential_passed=True,
                          case_count=report['cases'][op],
                          fixture_sha256=digest(vectors),
                          fixture=str(vectors.relative_to(library)),
                          oracle_metadata_sha256=digest(directory/'arm-oracle.json'),
                          test_log='evidence/recovery/2026-10-26/mixer-dsp/final-format-replay.log',
                          test_log_sha256=digest(evidence/'final-format-replay.log'),
                          hardware_validated=False, arm_abi_compatible=False)
            if op in ('N','R','G'):
                record.update(portable_ready=True, status='validated portable source; coordinator integration pending',
                              signature='float return established by ARM soft-float result/call flow; original parameter/member/const scope retained',
                              coverage=('1000 deterministic random input bit patterns plus 18 boundary inputs; not exhaustive'
                                        if op=='G' else '13104 boundary/adversarial configured-state cases, including endpoints, out-of-range requested midpoint, signed zero, NaN and infinity; not exhaustive'))
                name = f'{role}-{op}.json'
                (out/name).write_text(json.dumps(record, indent=2)+'\n')
                records.append(dict(role=role, mangled=symbol['mangled'],
                                    validation='validation/mixer-dsp/'+name,
                                    validation_sha256=digest(out/name)))
            else:
                record.update(portable_ready=False, status='pending original declaration',
                              unresolved=report['signature_caveats'][op])
                pending.append(record)
    (out/'pending-functions.json').write_text(json.dumps(pending, indent=2)+'\n')
    (out/'sealed-functions.json').write_text(json.dumps(dict(
        records=records, pending_file='validation/mixer-dsp/pending-functions.json',
        sources=sources, formatting=formatter, central_ledger_modified=False,
        note='Reference oracle JSON cpp_differential_passed=false is a generator placeholder. The separate sealed C++ replay log establishes the differential result.'), indent=2)+'\n')
    (out/'README.md').write_text('''# DSP recovery validation

Three original numeric methods are validated as portable source within the
recorded fixture domain. The two Bilinear numeric methods pass against both
mixer 13731 and surface 13840. Shelby gain is present in the server fixture.
See `sealed-functions.json` and its five per-binary records.

The setters pass state comparisons, but their original return declarations
remain unresolved. The EQ lookup passes four valid indices, but its return
enum/type remains unresolved. These stay in `pending-functions.json`.

Use `-fno-fast-math -ffp-contract=off`; the runner checks FE_TONEAREST and
gradual underflow with FTZ/DAZ disabled. Soft-float NaN payload/sign behavior
is preserved explicitly. Tests compare return bits and state, not floating
exception flags. No original object ABI or hardware compatibility is claimed.

The oracle generator metadata is reference evidence only. Its placeholder
`cpp_differential_passed=false` does not describe the separate C++ replay;
the sealed replay log records both passing C++ runs.
''')
    checkpoint = json.loads((out/'checkpoint.json').read_text())
    checkpoint.update(state='resumed replay complete; sealed records await coordinator integration',
                      source_hashes=sources, owned_live_jobs=[],
                      client_differential_result=dict(passed=True, cases=27846),
                      sealed_manifest='validation/mixer-dsp/sealed-functions.json')
    checkpoint['pending']['current_source_replay'] = 'Completed after final formatting; see final-format-replay.log.'
    checkpoint['pending']['client_validation'] = 'Completed successfully for four Bilinear methods; setters remain declaration-pending.'
    (out/'checkpoint.json').write_text(json.dumps(checkpoint, indent=2)+'\n')
    print(f'Sealed {len(records)} per-binary numeric records; {len(pending)} declaration-pending records.')

if __name__ == '__main__':
    main()
