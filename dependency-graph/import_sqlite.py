"""Measure CSV ingestion separately from expensive source-map extraction."""
import argparse
import csv
import json
import pathlib
import sqlite3
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run', required=True)
parser.add_argument('--integer-keys', action='store_true')
args = parser.parse_args()
run = pathlib.Path(args.run)
path = run / ('csv-import-int.sqlite' if args.integer_keys else 'csv-import.sqlite')
if path.exists():
    raise ValueError('Never overwrite a prior benchmark')
c = sqlite3.connect(path)
start = time.perf_counter()
node_schema = ('pk INTEGER PRIMARY KEY,id TEXT UNIQUE,kind TEXT,label TEXT,metadata TEXT'
               if args.integer_keys else 'id TEXT PRIMARY KEY,kind TEXT,label TEXT,metadata TEXT')
key = 'INTEGER' if args.integer_keys else 'TEXT'
ref = 'pk' if args.integer_keys else 'id'
c.executescript('CREATE TABLE nodes(' + node_schema + '); CREATE TABLE edges(src ' + key +
               ' REFERENCES nodes(' + ref + '),dst ' + key + ' REFERENCES nodes(' + ref +
               '),kind TEXT,evidence TEXT, PRIMARY KEY(src,dst,kind,evidence)); '
               'CREATE INDEX reverse_edges ON edges(dst,kind,src);')
phases = {}
ids = {}
for table in ('nodes', 'edges'):
    phase = time.perf_counter()
    count = 0
    with (run / (table + '.csv')).open() as stream:
        reader = csv.reader(stream)
        next(reader)
        batch = []
        for row in reader:
            if args.integer_keys and table == 'edges':
                row = [ids[row[0]], ids[row[1]], row[2], row[3]]
            batch.append(row)
            count += 1
            if len(batch) == 2000:
                c.executemany('INSERT INTO ' + table +
                              ('(id,kind,label,metadata)' if table == 'nodes' else '') +
                              ' VALUES(?,?,?,?)', batch)
                c.commit()
                batch = []
        if batch:
            c.executemany('INSERT INTO ' + table +
                          ('(id,kind,label,metadata)' if table == 'nodes' else '') +
                          ' VALUES(?,?,?,?)', batch)
            c.commit()
    phases[table] = {'rows': count, 'seconds': time.perf_counter() - phase}
    if table == 'nodes' and args.integer_keys:
        ids = dict(c.execute('SELECT id,pk FROM nodes'))
c.close()
(run / ('sqlite-int-online-import.json' if args.integer_keys else 'sqlite-online-import.json')).write_text(json.dumps({
    'phases': phases, 'seconds': time.perf_counter() - start, 'batch': 2000,
    'bytes': path.stat().st_size, 'indexes_present_during_import': True}, indent=2) + '\n')
print(json.dumps(phases))
