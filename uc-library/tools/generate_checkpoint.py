"""Summarize the active SQLite registry; this does not replace readiness validation."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / 'registry'))
from adapter import RegistrySnapshot, resolve_db


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(library, repository, phase, db=None):
    inputs = {}
    integration_path = library / 'validation' / 'integration.json'
    integration = json.loads(integration_path.read_text())
    inputs[str(integration_path.relative_to(repository))] = sha256(integration_path)
    with RegistrySnapshot(resolve_db(library, db)) as registry:
        ready = registry.load_registry('ready')['functions']
        pending = registry.load_registry('pending')['functions']
        registry_provenance = registry.provenance()
    identities = lambda rows: {(r['original_elf_sha256'], r['mangled']) for r in rows}
    ready_keys, pending_keys = identities(ready), identities(pending)
    if len(ready_keys) != len(ready) or len(pending_keys) != len(pending):
        raise ValueError('Duplicate original identities in a ledger')
    if ready_keys & pending_keys:
        raise ValueError('Ready/pending identities overlap')
    if integration.get('platform') != 'linux' or integration.get('ctest_passed') is not True:
        raise ValueError('Current integration must report passing Linux validation')
    test_log = (repository / integration['test_log']).resolve()
    if not test_log.is_relative_to(repository) or sha256(test_log) != integration['test_log_sha256']:
        raise ValueError('Integration test log hash/path mismatch')
    return dict(
        registry=registry_provenance, phase=phase, generated_at=datetime.now(timezone.utc).isoformat(), inputs=inputs,
        ready_entries=len(ready), ready_distinct_mangles=len({r['mangled'] for r in ready}),
        declaration_pending_entries=len(pending),
        roles=dict(Counter(r.get('role', 'unspecified') for r in ready)),
        test_suites=integration['test_suites'], platform='linux',
        ready_identities=sorted([list(k) for k in ready_keys]),
        pending_identities=sorted([list(k) for k in pending_keys]),
        scope='Portable source reconstruction only; no ARM ABI or hardware completion claim.',
        validation='Metadata summary with ledger-disjointness and test-log hash checks; run the full checkpoint audit separately.',
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', type=Path, required=True)
    parser.add_argument('--repository', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='Project temp/ Markdown; paired JSON is written beside it')
    parser.add_argument('--phase', required=True)
    parser.add_argument('--db', type=Path, help='Explicit registry database; defaults to validation/registry-sqlite/ACTIVE.json')
    parser.add_argument('--baseline', type=Path, help='Previous generated checkpoint JSON for identity deltas')
    args = parser.parse_args()
    repository = args.repository.resolve()
    output = args.output.resolve()
    library = args.library.resolve()
    if not output.is_relative_to(repository / 'temp') or not library.is_relative_to(repository):
        parser.error('Library must be in the project; checkpoint output must be in project temp/')
    if output.suffix != '.md' or output.exists() or output.with_suffix('.json').exists():
        parser.error('Use a new .md checkpoint path; existing artifacts are preserved')
    result = snapshot(library, repository, args.phase, args.db)
    if args.baseline:
        previous = json.loads(args.baseline.read_text())
        result['baseline_sha256'] = sha256(args.baseline)
        result['delta'] = {}
        for kind in ('ready', 'pending'):
            old = {tuple(k) for k in previous[kind + '_identities']}
            current = {tuple(k) for k in result[kind + '_identities']}
            result['delta'][kind] = dict(added=sorted(current - old), removed=sorted(old - current))
    text = [f"# {args.phase}", '',
            f"{result['ready_entries']} portable-ready per-ELF entries / "
            f"{result['ready_distinct_mangles']} distinct ready mangles; "
            f"{result['declaration_pending_entries']} declaration-pending entries (disjoint).",
            f"Current Linux integration reports {result['test_suites']} passing suites; test-log hash checked.",
            '', result['scope'], result['validation'], '', '## Bound inputs', '']
    text.extend(f'- `{path}`: `{digest}`' for path, digest in result['inputs'].items())
    text.extend(['', '## Registry snapshot', '', '```json', json.dumps(result['registry'], indent=2), '```'])
    if 'delta' in result:
        text.extend(['', '## Changes from previous generated checkpoint', ''])
        for kind, delta in result['delta'].items():
            text.append(f"- {kind}: +{len(delta['added'])} / -{len(delta['removed'])} original identities.")
        text.append('Full changed identities are retained in the paired JSON.')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.with_suffix('.json').write_text(json.dumps(result, indent=2) + '\n')
    output.write_text('\n'.join(text) + '\n')
    print(json.dumps({key: result[key] for key in ('phase', 'ready_entries', 'ready_distinct_mangles', 'declaration_pending_entries', 'test_suites')}))
    print(str(output))


if __name__ == '__main__':
    main()
