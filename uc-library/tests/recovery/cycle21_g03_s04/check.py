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
    lines = run(exe, '4', *(str(int(arg)) for arg in case['args'])).splitlines()
    offset, notified, visibility_probes = map(int, lines[0].split())
    observer_order = [int(value) for value in lines[1].split()]
    labels_and_targets = [line.rsplit(' ', 1) for line in lines[2:]]
    labels = [label for label, _ in labels_and_targets]
    targets = [int(target) or None for _, target in labels_and_targets]
    assert offset == case['offset'] and notified == case['last_notified']
    assert observer_order == [entry[1] for entry in case['trace'] if entry[0] == 'observer']
    assert visibility_probes == case['trace'].count(['visible'])
    assert labels == (case['labels'] or [''] * 16)
    assert targets == (case['targets'] or [None] * 16)
    return dict(native=case, labels=labels, targets=targets, observer_order=observer_order)


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
    domain = 'Visible and hidden page, unchanged and changed scroll offsets, upper clamp, ordered observers, all 16 labels and exact named alias targets including disconnections.'
    root = Path(__file__).resolve().parents[4]
    sources = ['src/Presonus/Surface/PageObservers.cpp', 'include/presonus/surface/sl_mixer_encoder.hpp']
    providers = ['third_party/ccl-framework/core/portable/corecomponent.h', 'third_party/ccl-framework/core/portable/corecomponent.cpp', 'third_party/ccl-framework/core/portable/coreparams.h', 'third_party/ccl-framework/core/portable/coreparams.cpp', 'third_party/ccl-framework/core/portable/coreparaminfo.h', 'third_party/ccl-framework/core/public/corevector.h', 'third_party/ccl-framework/core/public/corestringbuffer.h', 'third_party/ccl-framework/core/public/corestringtraits.h']
    row = dict(original_elf_sha256=fixture['elf_sha256'], mangled=fixture['mangled'],
               original_address=fixture['address'], cpp_compiled=True,
               mangling_namespace_checked=True, portable_ready=False,
               validation_domain=domain, domain=domain,
               declaration_uncertainties=['Original C++ ordinary return declaration and original class layout remain unresolved. The portable member uses void; observed side effects are scoped.'],
               sources={name: sha(root / 'uc-library' / name) for name in sources},
               repository_sources={name: sha(root / name) for name in providers})
    receipt = dict(replay_passed=True, cpp_differential_passed=True,
                   compiled_mangled_names_matched=True, mangled_names=[fixture['mangled']],
                   functions=[row], proposed_readiness={'ready': [], 'pending': [row]},
                   validation_domain=domain, results=results, case_count=len(results),
                   args=vars(args), object_sha256=sha(args.object),
                   integration_sha256=integration_hash, fixtures_sha256=sha(args.fixture))
    out = Path(args.out)
    out.parent.mkdir(exist_ok=True, parents=True)
    out.write_text(json.dumps(receipt, indent=2) + '\n')
    print(f"Replay observed {len(results)} native/portable cases for {fixture['task_id']}")


if __name__ == '__main__':
    main()
