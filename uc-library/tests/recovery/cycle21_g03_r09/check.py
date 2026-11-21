import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from native import generate


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def replay(exe, case):
    text = ' '.join(str(value) for value in case['table']) + '\n'
    portable = int(subprocess.check_output([exe], input=text, text=True))
    assert portable == case['count']
    return dict(native=case, portable_count=portable)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--exe', required=True)
    parser.add_argument('--object', required=True)
    parser.add_argument('--fixture', required=True)
    parser.add_argument('--integration', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--symbols-only', action='store_true')
    args = parser.parse_args()
    fixture = json.loads(Path(args.fixture).read_text())
    symbols = run('/usr/bin/nm', '--defined-only', args.object)
    assert fixture['mangled'] in [row.split()[-1] for row in symbols.splitlines()]
    if args.symbols_only:
        return
    assert fixture == generate()
    results = [replay(args.exe, case) for case in fixture['cases']]
    integration = Path(args.integration)
    integration_hash = sha(integration) if integration.is_file() else None
    domain = 'Readable signed 32-bit tables with -1 sentinel: empty, early termination, zero, other negative and integer extreme values, and 256 elements.'
    root = Path(__file__).resolve().parents[4]
    sources = ['src/utilities/TableElements.cpp', 'include/presonus/utilities/table_elements.hpp']
    providers = []
    decision = 'pending'
    row = dict(original_elf_sha256=fixture['elf_sha256'], mangled=fixture['mangled'],
               original_address=fixture['address'], cpp_compiled=True,
               mangling_namespace_checked=True, portable_ready=decision == 'ready',
               validation_domain=domain, domain=domain,
               sources={name: sha(root / 'uc-library' / name) for name in sources},
               repository_sources={name: sha(root / name) for name in providers})
    row['declaration_uncertainties'] = ['The ARM word count is returned in R0. The exact original C++ return type remains unencoded and unresolved. The portable definition returns int.']
    proposed = {'ready': [], 'pending': []}
    proposed[decision].append(row)
    receipt = dict(replay_passed=True, validation_domain=domain, results=results,
                   case_count=len(results), args=vars(args), object_sha256=sha(args.object),
                   integration_sha256=integration_hash, fixtures_sha256=sha(args.fixture))
    receipt.update(cpp_differential_passed=True, compiled_mangled_names_matched=True,
                   mangled_names=[fixture['mangled']], functions=[row],
                   proposed_readiness=proposed)
    out = Path(args.out)
    out.parent.mkdir(exist_ok=True, parents=True)
    out.write_text(json.dumps(receipt, indent=2) + '\n')
    print(f"Replay observed {len(results)} native/portable cases for {fixture['task_id']}")


if __name__ == '__main__':
    main()
