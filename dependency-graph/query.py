"""Read-only impact query with immediate edge evidence and timing samples."""
import argparse
import json
import pathlib
import sqlite3
import statistics
import time

from experiment import impact

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--db', required=True)
parser.add_argument('--path', required=True, help='Repository-relative path')
parser.add_argument('--domain', choices=('build', 'proof'), default='build')
parser.add_argument('--repeat', type=int, default=5)
args = parser.parse_args()
if args.repeat < 1:
    parser.error('--repeat must be positive')
c = sqlite3.connect(pathlib.Path(args.db).resolve().as_uri() + '?mode=ro', uri=True)
kinds = ('compiler_input', 'compiles', 'link_input') if args.domain == 'build' else (
    'proof_binding', 'validation_binding')
key = 'file:' + args.path
if not c.execute('SELECT 1 FROM nodes WHERE id=?', (key,)).fetchone():
    parser.error('Path not observed; absence does not prove independence')
samples = []
for _ in range(args.repeat):
    start = time.perf_counter()
    rows = impact(c, key, kinds)
    samples.append(time.perf_counter() - start)
ids = {r[0] for r in rows}
explanation = [r for r in c.execute('SELECT src,dst,kind,evidence FROM edges')
               if r[0] in ids and r[1] in ids and r[2] in kinds]
print(json.dumps({'affected': rows, 'explanation_edges': explanation,
                  'seconds': samples, 'median_seconds': statistics.median(samples),
                  'may_skip_checks': False}, indent=2))
