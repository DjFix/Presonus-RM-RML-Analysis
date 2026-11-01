"""Check persisted graph integrity and replay the known header observation."""
import argparse
import json
import pathlib
import sqlite3

from experiment import impact, sha

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run', required=True)
args = parser.parse_args()
run = pathlib.Path(args.run).resolve()
c = sqlite3.connect((run / 'graph.sqlite').as_uri() + '?mode=ro', uri=True)
assert c.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
assert not c.execute('PRAGMA foreign_key_check').fetchall()
report = json.loads((run / 'report.json').read_text())
assert sha(run / 'registry-snapshot.sqlite') == report['snapshot_sha256']
snapshot = sqlite3.connect((run / 'registry-snapshot.sqlite').as_uri() + '?mode=ro', uri=True)
assert snapshot.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
symbols = c.execute("SELECT count(*) FROM nodes WHERE kind='symbol'").fetchone()[0]
assert symbols == snapshot.execute('SELECT count(*) FROM records').fetchone()[0]
headers = c.execute("SELECT id FROM nodes WHERE label LIKE '%/ControlHelpers.hpp'").fetchall()
assert len(headers) == 1
closure = impact(c, headers[0][0], ('compiler_input', 'compiles', 'link_input'))
objects = [label for _, _, label in closure
           if '/CMakeFiles/presonus_' in label and '_objects.dir/' in label and label.endswith('.o')]
assert len(objects) == 5, objects
assert len(objects) == len(set(objects))
result = {'integrity': 'ok', 'registry_symbols': symbols,
          'control_helpers_production_objects': objects,
          'five_production_object_observation_replayed': True,
          'semantic_dependency_completeness_proven': False,
          'no_checks_may_be_skipped': True}
print(json.dumps(result, indent=2))
