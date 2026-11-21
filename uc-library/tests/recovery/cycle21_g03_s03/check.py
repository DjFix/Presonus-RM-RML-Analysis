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
    calls = case['calls']
    assert calls[0] == ['findParameter', 'selected_mix']
    exists = case['parameter_exists']
    available = case['target_exists']
    providers = [call for call in calls if call[0] in ('getMainGeq', 'getMixGeq')]
    assert len(providers) <= 1
    child = None
    omitted = -1
    if providers:
        name, arg = providers[0]
        if name == 'getMixGeq':
            assert calls[1:4] == [['getValue'], ['getNumMixGeqs'], [name, arg]]
            child = f'Mix{arg}'
            omitted = arg if not available else -1
        else:
            assert calls[1:3] == [['getValue'], [name, arg]]
            child = 'Main' if arg == 0 else 'Alternate'
            omitted = 20 + arg if not available else -1
    if not providers:
        assert calls[1:] == ([['getValue'], ['getNumMixGeqs']] if exists else [])
    argv = (exe, str(int(exists)), str(case['value']), str(case['count']), str(omitted))
    output = run(*argv, 'page')
    if available:
        assert calls[-1] == ['getComponentPath']
        expected = run(*argv, child)
    else:
        assert ['getComponentPath'] not in calls
        expected = 'unchanged'
    assert output == expected
    return dict(native=case, portable_url=output, expected_url=expected)


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
    domain = 'Missing named parameter, mix indices below/at count, 19/20 boundary, fractional inputs, both main targets, and null slots preserve existing output; named CCL component paths.'
    receipt = dict(replay_passed=True, validation_domain=domain, results=results,
                   case_count=len(results), args=vars(args),
                   object_sha256=sha(args.object), integration_sha256=integration_hash,
                   fixtures_sha256=sha(args.fixture))
    root = Path(__file__).resolve().parents[4]
    sources = ['src/Presonus/Surface/GeqPresetsPageComponent.cpp', 'include/presonus/surface/GeqPresetsPageComponent.hpp']
    providers = ['third_party/ccl-framework/core/portable/corecomponent.h', 'third_party/ccl-framework/core/portable/corecomponent.cpp', 'third_party/ccl-framework/core/portable/coreparams.h', 'third_party/ccl-framework/core/portable/coreparams.cpp', 'third_party/ccl-framework/core/public/corevector.h']
    decision = 'pending'
    row = dict(original_elf_sha256=fixture['elf_sha256'], mangled=fixture['mangled'],
               original_address=fixture['address'], cpp_compiled=True,
               mangling_namespace_checked=True, portable_ready=decision == 'ready',
               validation_domain=domain, domain=domain,
               sources={name: sha(root / 'uc-library' / name) for name in sources},
               repository_sources={name: sha(root / name) for name in providers})
    row['declaration_uncertainties'] = ['Original return declaration is absent from symbol mangling and early exits expose varying R0. The portable member uses void and a borrowed GEQ target binding.']
    proposed = {'ready': [], 'pending': []}
    proposed[decision].append(row)
    receipt.update(cpp_differential_passed=True, compiled_mangled_names_matched=True,
                   mangled_names=[fixture['mangled']], functions=[row],
                   proposed_readiness=proposed)
    out = Path(args.out)
    out.parent.mkdir(exist_ok=True, parents=True)
    out.write_text(json.dumps(receipt, indent=2) + '\n')
    print(f"Replay observed {len(results)} native/portable cases for {fixture['task_id']}")


if __name__ == '__main__':
    main()
