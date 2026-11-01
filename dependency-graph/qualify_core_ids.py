"""Qualify compiler-local Core IDs before publication; preserve prior observations."""
import csv
import hashlib
import json
import pathlib
import sqlite3

from gcc_source_graph import parse_dump

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUN = ROOT / 'dependency-graph/runs/core-source-01'
MAIN = ROOT / 'dependency-graph/runs/full-01'


def sha(path):
    return hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()


def qualified(key):
    if key.startswith('compiler:'):
        return key.replace('compiler:', 'compiler:core-source-01:', 1)
    if key.startswith('unresolved:gcc:'):
        return key.replace('unresolved:gcc:', 'unresolved:gcc:core-source-01:', 1)
    return key


def main():
    receipt = RUN / 'id-qualification.json'
    assert not receipt.exists()
    c = sqlite3.connect(MAIN / 'graph.sqlite')
    c.execute('CREATE TABLE core_rekey_previous_nodes(id TEXT,kind TEXT,label TEXT,metadata TEXT)')
    with (RUN / 'delta-nodes.csv').open() as stream:
        rows = list(csv.DictReader(stream))
    mapping = {row['id']: qualified(row['id']) for row in rows if qualified(row['id']) != row['id']}
    source_inputs = {'core_nodes': sha(RUN / 'delta-nodes.csv'),
                     'core_edges': sha(RUN / 'delta-edges.csv'),
                     'main_nodes': sha(MAIN / 'delta-nodes.csv')}
    compiler = next(RUN.glob('gcc-all-*'))
    parsed = {}
    for row in rows:
        old = row['id']
        if old not in mapping:
            continue
        previous = c.execute('SELECT * FROM nodes WHERE id=?', (old,)).fetchone()
        if previous:
            c.execute('INSERT INTO core_rekey_previous_nodes VALUES(?,?,?,?)', previous)
        row['id'] = mapping[old]
        meta = json.loads(row['metadata'])
        if old.startswith('compiler:'):
            _, index, number = old.split(':')
            if index not in parsed:
                proof = json.loads((compiler / f'{int(index):04d}.json').read_text())
                parsed[index] = parse_dump(pathlib.Path(proof['dump']).read_text())
            record = parsed[index][number]
            # The old colliding row may have inherited metadata from the main build.
            meta = {'mangled': None, 'compiler_printed_name': record['name'],
                    'compiler_definition': record['definition'], 'compiler_type': record['type'],
                    'source_port_declaration': True}
        meta['compiler_build_group'] = 'core-source-01'
        row['metadata'] = json.dumps(meta, sort_keys=True)
        c.execute('INSERT INTO nodes VALUES(?,?,?,?)',
                  tuple(row[k] for k in ('id','kind','label','metadata')))
    rewritten = 0
    with (RUN / 'delta-edges.csv').open() as source, (RUN / 'qualified-edges.csv').open('x') as target:
        reader = csv.DictReader(source)
        writer = csv.DictWriter(target, fieldnames=reader.fieldnames)
        writer.writeheader()
        for row in reader:
            previous = tuple(row[k] for k in ('src','dst','kind','evidence'))
            new_src = mapping.get(row['src'], row['src'])
            new_dst = mapping.get(row['dst'], row['dst'])
            if (new_src,new_dst) != (row['src'],row['dst']):
                root_fact = c.execute('SELECT 1 FROM delta_edges WHERE src=? AND dst=? AND kind=? AND evidence=?', previous).fetchone()
                if not root_fact:
                    c.execute('DELETE FROM edges WHERE src=? AND dst=? AND kind=? AND evidence=?', previous)
                row['src'],row['dst'] = new_src,new_dst
                c.execute('INSERT OR IGNORE INTO edges VALUES(?,?,?,?)',
                          tuple(row[k] for k in ('src','dst','kind','evidence')))
                rewritten += 1
            writer.writerow(row)
    root_rows = {}
    with (MAIN / 'delta-nodes.csv').open() as source:
        for row in csv.DictReader(source):
            if row['id'] in mapping:
                root_rows[row['id']] = row
    for old in mapping:
        if old in root_rows:
            row = root_rows[old]
            c.execute('UPDATE nodes SET kind=?,label=?,metadata=? WHERE id=?',
                      (row['kind'],row['label'],row['metadata'],old))
        else:
            assert not c.execute('SELECT 1 FROM edges WHERE src=? OR dst=? LIMIT 1', (old,old)).fetchone()
            c.execute('DELETE FROM nodes WHERE id=?', (old,))
    c.commit()
    with (RUN / 'qualified-nodes.csv').open('x') as stream:
        writer = csv.DictWriter(stream, fieldnames=('id','kind','label','metadata'))
        writer.writeheader()
        writer.writerows(rows)
    prior = json.loads((RUN / 'full-graph.json').read_text())
    prior.update(node_kinds=dict(c.execute('SELECT kind,count(*) FROM nodes GROUP BY kind')),
                 edge_kinds=dict(c.execute('SELECT kind,count(*) FROM edges GROUP BY kind')),
                 compiler_local_ids_qualified=True,
                 parent_observations_sha256=sha(RUN / 'full-graph.json'))
    (RUN / 'full-graph-qualified.json').write_text(json.dumps(prior, indent=2) + '\n')
    receipt.write_text(json.dumps({'input_sha256': source_inputs,
                                  'qualified_ids': len(mapping), 'rewritten_edges': rewritten,
                                  'root_node_rows_restored': len(root_rows),
                                  'previous_rows_preserved_in': 'core_rekey_previous_nodes',
                                  'source_sha256': sha(pathlib.Path(__file__))}, indent=2) + '\n')
    print(json.dumps({'qualified_ids':len(mapping), 'rewritten_edges':rewritten}))


if __name__ == '__main__':
    main()
