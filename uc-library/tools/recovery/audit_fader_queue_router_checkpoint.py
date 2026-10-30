"""Audit a mirrored source-bound Linux reconstruction checkpoint, without C++ builds."""
import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'registry'))
from adapter import snapshot

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--ready',type=int,required=True)
parser.add_argument('--pending',type=int,required=True)
parser.add_argument('--mangles',type=int,required=True)
parser.add_argument('--suites',type=int,required=True)
parser.add_argument('--phase',required=True)
parser.add_argument('--registry-db',type=Path,help='Explicit SQLite registry; defaults to ACTIVE')
parser.add_argument('--repository',type=Path,default=Path(__file__).resolve().parents[3])
parser.add_argument('--output',type=Path)
args=parser.parse_args()
repo=args.repository.resolve()
lib=repo/'uc-library'
spec=importlib.util.spec_from_file_location('readiness',lib/'tools/merge_readiness.py')
checks=importlib.util.module_from_spec(spec);spec.loader.exec_module(checks)
cache=checks.ValidationCache()
sha=cache.sha
def read(name):
    return cache.read_json(lib/name)
integration=read('validation/integration.json')
assert integration==read('validation/integration-linux.json')
assert integration['platform']=='linux' and integration['ctest_passed']
assert integration['test_suites']==args.suites
for name,digest in integration['files'].items():
    assert sha(lib/name)==digest,name
for name,digest in integration['logs'].items():
    assert sha(repo/name)==digest,name
with snapshot(lib,args.registry_db) as registry:
    ready=registry.ready['functions']
    pending=registry.pending['functions']
    registry_source=registry.provenance()
ready_keys={(row['original_elf_sha256'],row['mangled']) for row in ready}
pending_keys={(row['original_elf_sha256'],row['mangled']) for row in pending}
assert len(ready_keys)==len(ready) and len(pending_keys)==len(pending),'duplicate original identity'
assert ready_keys.isdisjoint(pending_keys),'ready/pending status overlap'
assert len(ready)==args.ready and len(pending)==args.pending
assert len({row['mangled'] for row in ready})==args.mangles
proofs={}
checked_sources={}
for row in ready+pending:
    proof_path=lib/row['validation']
    assert sha(proof_path)==row['validation_sha256'],row['mangled']
    sources=row['sources']
    if checked_sources.get(id(sources)) is not sources:
        for name,digest in sources.items():
            assert sha(lib/name)==digest,name
        checked_sources[id(sources)]=sources
    assert checks.repository_sources_match(lib,row,cache),row['mangled']
    if row.get('portable_ready'):
        assert isinstance(row.get('domain'),str) and row['domain'].strip()
        if proof_path not in proofs:
            proofs[proof_path]=cache.read_json(proof_path)
        assert checks.proof_covers(proofs[proof_path],row),row['mangled']
coverage=read('tracking/coverage.json')['roles']
assert sum(role['summary']['portable_reconstructions_ready'] for role in coverage.values())==args.ready
assert sum(role['summary']['compiled_declaration_pending_entries'] for role in coverage.values())==args.pending
cache.unchanged()
report=dict(passed=True,canonical_platform='linux',ready_entries=args.ready,
    canonical_statuses_disjoint=True,
    pending_entries=args.pending,distinct_mangles=args.mangles,suites=args.suites,
    integrated_inputs=len(integration['files']),source_hashes_checked=len(cache.files),
    integration_sha256=sha(lib/'validation/integration.json'),
    registry_source=registry_source,
    symbols_sha256=sha(lib/'SYMBOLS.md'),
    original_arm_abi_verified=False,hardware_verified=False,
    scope='Local mirror source/proof hashes and explicit upstream dependencies; Linux build evidence, no local C++ validation')
cache.unchanged()
out=args.output.resolve() if args.output else repo/'evidence/recovery/2026-10-28'/args.phase/'checkpoint-audit.json'
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
