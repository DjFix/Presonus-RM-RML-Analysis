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
    output = [int(value) for value in run(exe, '7', *map(str, case['args'])).split()]
    assert output[1:] == [case['offset'], case['trace'].count(['refresh'])]
    assert case['trace'][0] == ['base', case['args'][2]]
    assert output[0] == int(case['args'][2] == 3)
    return dict(native=case, pinned_component_dirty=output[0], portable_offset=output[1],
                portable_refresh_count=output[2])


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
    domain = 'Real CCL storable numeric parameters with tags 1000, 1001 and unrelated tag, message gating, positive/zero/negative values, and observable base dirty/refresh state.'
    root = Path(__file__).resolve().parents[4]
    sources = ['src/Presonus/Surface/PageObservers.cpp', 'include/presonus/surface/sl_mixer_encoder.hpp']
    providers = ['third_party/ccl-framework/core/portable/corecomponent.h', 'third_party/ccl-framework/core/portable/corecomponent.cpp', 'third_party/ccl-framework/core/portable/coreparams.h', 'third_party/ccl-framework/core/portable/coreparams.cpp', 'third_party/ccl-framework/core/portable/coreparaminfo.h', 'third_party/ccl-framework/core/public/corevector.h']
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
