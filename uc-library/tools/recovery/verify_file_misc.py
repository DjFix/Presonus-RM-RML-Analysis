"""Audit and inventory the completed UC integration phase on either checkout."""
import hashlib
import json
import argparse
from pathlib import Path

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--phase',default='file-misc-integration')
parser.add_argument('--ready',type=int,default=268)
parser.add_argument('--methods',type=int,default=139)
parser.add_argument('--suites',type=int,default=22)
parser.add_argument('--inputs',type=int,default=94)
parser.add_argument('--headers',type=int,default=24)
parser.add_argument('--attempt',default='release-strict')
args=parser.parse_args()

repo = Path('/home/rs/projects/opencs/ai-line-analysis')
lib = repo / ('uc-library' if (repo / 'uc-library').is_dir() else 'uc-library')
phase = repo / 'evidence/recovery/2026-10-27' / args.phase
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
seals = [json.loads((lib / ('validation/' + name)).read_text()) for name in ('integration.json', 'integration-linux.json')]
assert seals[0]['files'] == seals[1]['files']
assert len(seals[0]['files']) == args.inputs
for seal in seals:
    assert seal['ctest_passed'] and seal['test_suites'] == args.suites
    for name, digest in seal['files'].items():
        assert sha(lib / name) == digest, name
    for name, digest in seal['logs'].items():
        assert sha(repo / name) == digest, name
ready = json.loads((lib / 'validation/ready-functions.json').read_text())['functions']
assert len(ready) == args.ready and len({r['mangled'] for r in ready}) == args.methods
for r in ready:
    assert sha(lib / r['validation']) == r['validation_sha256']
    for name, digest in r['sources'].items():
        assert sha(lib / name) == digest, name
for platform in ('mac', 'linux'):
    directory=phase/platform
    if args.attempt != 'initial': directory=directory/args.attempt
    audit = json.loads((directory/'install-audit.json').read_text())
    assert audit['header_set_matches'] and audit['compiled_mangles_matched']
    assert len(audit['public_header_hashes']) == args.headers
    assert set(audit['ready_original_mangles']) == {r['mangled'] for r in ready}
manifest = {str(p.relative_to(repo)): sha(p) for p in sorted(phase.rglob('*')) if p.is_file() and p.name != 'manifest.json'}
destination = phase / 'manifest.json'
destination.write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps(dict(ready_entries=len(ready), original_methods=args.methods, test_suites=args.suites, canonical_platform=seals[0]['platform'], proof_platforms=sorted({s['platform'] for s in seals}), unchanged_inputs=args.inputs, public_headers=args.headers, evidence_files=len(manifest), manifest_sha256=sha(destination))))
