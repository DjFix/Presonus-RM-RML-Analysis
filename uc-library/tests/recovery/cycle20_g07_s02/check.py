"""Replay the canonical Linux Book source against independently observed ARM fixtures."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

GETTER = False
TARGET = '_ZN8Presonus5Panel4Book10togglePageEv'
DOMAIN = ('Seven receiver patterns per original ARM base entry with no external or '
          'receiver accesses. Host invokes the direct typed base member on both real Book '
          'states and checks owned state, borrowed page markers, and intact slot pointers.')
ROOT = Path(__file__).resolve().parents[4]
SOURCES = ('src/Presonus/Panel/Book.cpp', 'include/presonus/panel/Book.hpp')
CCL = 'third_party/ccl-framework/core/public/corevector.h'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures', required=True, type=Path)
    parser.add_argument('--exe', required=True, type=Path)
    parser.add_argument('--object', required=True, type=Path)
    parser.add_argument('--integration', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()

    symbols = subprocess.check_output(['nm', '--defined-only', str(args.object)], text=True)
    matching = [line for line in symbols.splitlines() if line.split()[-1:] == [TARGET]]
    if len(matching) != 1:
        raise RuntimeError(f"Expected one compiled definition of {TARGET}: {matching}")

    fixture = json.loads(args.fixtures.read_text())
    fixture_rows = fixture['originals']
    if len(fixture_rows) != 2 or {row['role'] for row in fixture_rows} != {'client', 'server'}:
        raise RuntimeError("Expected two separate native original identities")
    rows = []
    for original in fixture_rows:
        if original['mangled'] != TARGET or len(original['cases']) != 7:
            raise RuntimeError("Fixture target or domain differs")
        for case in original['cases']:
            if GETTER:
                argv = [str(case['tag'])]
                expected = f"{case['word']} 0"
            else:
                argv = [str(case['tag']), str(case['receiver_pattern'])]
                expected = str(int(case['receiver_unchanged'] and not case['receiver_accesses']))
            actual = subprocess.check_output([str(args.exe.resolve()), *argv], text=True).strip()
            if actual != expected:
                raise RuntimeError(f"{original['role']} {argv}: expected {expected!r}, got {actual!r}")
        row = {key: value for key, value in original.items() if key != 'cases'}
        row.update(original_address=original['address'], case_count=len(original['cases']),
                   cpp_compiled=True, mangling_namespace_checked=True, portable_ready=False,
                   domain=DOMAIN, hardware_verified=False, original_function_verified=False,
                   declaration_uncertainties=['Original ordinary return declaration remains unresolved.',
                                              'Portable state and calling conventions are scoped to the Linux source port.'],
                   sources={name: digest(ROOT / 'uc-library' / name) for name in SOURCES},
                   repository_sources={CCL: digest(ROOT / CCL)})
        rows.append(row)

    integration = Path(args.integration)
    proof = dict(replay_passed=True, arm_differential_passed=True,
                 compiled_mangled_names_matched=True, mangling_namespace_checked=True,
                 portable_ready=False, domain=DOMAIN, mangled_names=[TARGET],
                 proposed_readiness={'ready': [], 'pending': rows},
                 functions=rows, observations=sum(row['case_count'] for row in rows),
                 fixture_sha256=digest(args.fixtures), producer_sha256=digest(Path(__file__)),
                 object_sha256=digest(args.object), executable_sha256=digest(args.exe),
                 integration_sha256=digest(integration) if integration.is_file() else None,
                 symbol_output=matching)
    if args.out != '-':
        Path(args.out).write_text(json.dumps(proof, indent=2) + '\n')
    print(f"{proof['observations']} {TARGET} observations matched")


if __name__ == '__main__':
    main()
