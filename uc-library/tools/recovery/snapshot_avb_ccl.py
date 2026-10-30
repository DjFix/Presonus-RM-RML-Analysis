"""Preserve this phase's fresh active-path proofs and artifacts in evidence."""
import hashlib
import json
from pathlib import Path
import shutil
import argparse

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run', required=True)
args = parser.parse_args()
assert Path(args.run).name == args.run and args.run not in ('.', '..')

repo = Path('/home/rs/projects/opencs/ai-line-analysis')
lib = repo / 'uc-library'
assert lib.is_dir(), 'Run on the Linux analysis checkout'
source = lib / 'validation/avb-lookup-active/runs' / args.run
target = repo / 'evidence/recovery/2026-10-27/avb-ccl-root' / ('active-proof-'+args.run)
assert not target.exists(), 'Preserve an existing snapshot; do not overwrite it'
shutil.copytree(source, target)
files = {str(path.relative_to(target)):hashlib.sha256(path.read_bytes()).hexdigest()
         for path in sorted(target.rglob('*')) if path.is_file()}
(target.parent / ('active-proof-'+args.run+'-manifest.json')).write_text(json.dumps(files, indent=2)+'\n')
print(json.dumps({'preserved_files':len(files), 'evidence':str(target.relative_to(repo))}))
