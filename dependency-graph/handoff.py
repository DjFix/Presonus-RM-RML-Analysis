"""Build a bounded code-reading packet; broad proof bindings stay references."""
import argparse
import hashlib
import json
import pathlib
import re
import sqlite3
import subprocess
import time

from graph_query import impact

ROOT = pathlib.Path(__file__).resolve().parents[1]


def readonly(path):
    return sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)


def index(run):
    target = run / 'ownership.sqlite'
    if target.exists():
        raise ValueError('Never overwrite ownership observations')
    g = readonly(run / 'graph.sqlite')
    c = sqlite3.connect(target)
    c.executescript('''CREATE TABLE objects(id TEXT PRIMARY KEY,source TEXT,sha256 TEXT);
      CREATE TABLE definitions(object_id TEXT,mangled TEXT,PRIMARY KEY(object_id,mangled));
      CREATE INDEX definitions_by_symbol ON definitions(mangled,object_id);
      CREATE TABLE original_symbols(id TEXT PRIMARY KEY,mangled TEXT);
      CREATE INDEX original_names ON original_symbols(mangled,id);''')
    start = time.perf_counter()
    objects = g.execute('''SELECT e.src,n.label FROM edges e JOIN nodes n ON n.id=e.dst
      WHERE e.kind='compiles' AND n.label LIKE 'uc-library/src/%' ORDER BY e.src''').fetchall()
    for obj, source in objects:
        path = ROOT / obj.removeprefix('file:')
        before = hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()
        result = subprocess.run(['nm', '--defined-only', '--extern-only', '--format=posix', str(path)],
                                check=True, text=True, capture_output=True)
        after = hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()
        if before != after:
            raise ValueError('Object changed during nm: ' + str(path))
        c.execute('INSERT INTO objects VALUES(?,?,?)', (obj, source, before))
        c.executemany('INSERT OR IGNORE INTO definitions VALUES(?,?)',
                      [(obj, line.split()[0]) for line in result.stdout.splitlines() if line.split()])
    c.executemany('INSERT INTO original_symbols VALUES(?,?)',
                  g.execute("SELECT id,label FROM nodes WHERE kind='symbol'"))
    c.commit()
    result = {'production_objects': len(objects), 'seconds': time.perf_counter() - start,
              'nm_version': subprocess.check_output(['nm', '--version'], text=True).splitlines()[0],
              'exact_name_anchored_originals': c.execute('''SELECT count(DISTINCT s.id)
                FROM original_symbols s JOIN definitions d ON d.mangled=s.mangled''').fetchone()[0],
              'scope': 'Host object definitions by exact mangled identity; TU-level reading anchors, not ARM ABI proof'}
    (run / 'ownership-index.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


def packet(run, path, output):
    if output.exists():
        raise ValueError('Never overwrite a packet')
    start = time.perf_counter()
    g = readonly(run / 'graph.sqlite')
    ownership = readonly(run / 'ownership.sqlite')
    key = 'file:' + path
    if not g.execute('SELECT 1 FROM nodes WHERE id=?', (key,)).fetchone():
        raise ValueError('Unobserved input; cannot infer independence')
    # Reading scope intentionally stops at compilation, before archive fanout.
    affected = impact(g, key, ('compiler_input', 'compiles'))
    affected_ids = {r[0] for r in affected}
    objects = [row for row in ownership.execute('SELECT id,source,sha256 FROM objects')
               if row[0] in affected_ids]
    files = sorted({path, *(row[1] for row in objects)})
    for obj, source, digest in objects:
        observed = hashlib.file_digest((ROOT / obj.removeprefix('file:')).open('rb'), 'sha256').hexdigest()
        if observed != digest:
            raise ValueError('Ownership index stale: ' + obj)
    symbols = {}
    for obj, source, digest in objects:
        for original, mangled in ownership.execute('''SELECT s.id,s.mangled FROM original_symbols s
          JOIN definitions d ON d.mangled=s.mangled WHERE d.object_id=?''', (obj,)):
            symbols.setdefault(original, {'mangled': mangled, 'defined_in': []})['defined_in'].append(source)
    if symbols:
        values = list(symbols.values())
        demangled = subprocess.run(['c++filt'], input='\n'.join(v['mangled'] for v in values) + '\n',
                                   text=True, capture_output=True, check=True).stdout.splitlines()
        for item, name in zip(values, demangled, strict=True):
            item['demangled'] = name
    # Show direct project/Core include choices without dumping their transitive closure.
    observed_inputs = {r[0] for obj, _, _ in objects for r in g.execute(
        "SELECT n.label FROM edges e JOIN nodes n ON n.id=e.dst WHERE e.src=? AND e.kind='compiler_input'", (obj,))}
    on_demand = set()
    for source in files:
        for include in re.findall(r'^\s*#\s*include\s*"([^"]+)"', (ROOT / source).read_text(), re.M):
            on_demand.update(p for p in observed_inputs if p.endswith('/' + include) and p not in files)
    proof_paths = sorted({r[0] for identity in symbols for r in g.execute(
        "SELECT n.label FROM edges e JOIN nodes n ON n.id=e.dst WHERE e.src=? AND e.kind='validation_binding'", (identity,))})
    manifest_bound = {row[0] for row in g.execute('''SELECT src FROM edges WHERE dst=?
       AND kind IN ('proof_binding','validation_binding')''', (key,))}
    unmatched = sorted(manifest_bound - set(symbols))
    lines = ['# Agent reading packet', '', 'Changed input: `' + path + '`', '',
             '## Read first', '', *['- `' + f + '` — changed input or compiler-observed dependent TU' for f in files],
             '', '## Exact original symbols anchored in these host objects', '']
    for identity, item in sorted(symbols.items()):
        lines.append('- `' + item['demangled'] + '` — ' + ', '.join(item['defined_in']) +
                     '; ELF ' + identity.split(':')[1][:12])
    lines += ['', '## Read on demand: direct project/Core headers', '',
              *['- `' + f + '`' for f in sorted(on_demand)],
              '', '## Validation entry points for selected symbols', '',
              *['- `' + f + '`' for f in proof_paths]]
    lines += ['', '## Boundaries', '',
              'This packet selects reading context, not validation exemptions. It stops before link/archive fanout.',
              'Definitions are at TU scope. Call/type/virtual-dispatch relationships remain uncollected.',
              'Broad manifest-only bindings remain in the JSON appendix for escalation; they are not automatically code dependencies.',
              'Weak/inline symbols can occur in several objects. Exact mangling alone does not prove ARM ABI fidelity.']
    markdown = '\n'.join(lines) + '\n'
    output.write_text(markdown)
    result = {'changed_input': path, 'read_files': files,
              'production_objects': [{'id': o, 'source': s, 'sha256': h} for o, s, h in objects],
              'anchored_original_symbols': symbols,
              'read_on_demand': sorted(on_demand), 'validation_entry_points': proof_paths,
              'reading_source_sha256': {f: hashlib.file_digest((ROOT / f).open('rb'), 'sha256').hexdigest()
                                        for f in files + sorted(on_demand)},
              'manifest_bound_originals': len(manifest_bound),
              'manifest_only_unresolved_appendix': unmatched,
              'packet_bytes': len(markdown.encode()),
              'read_source_bytes': sum((ROOT / f).stat().st_size for f in files),
              'query_and_packet_seconds': time.perf_counter() - start,
              'scope': 'reading context only; direct compilation dependency slice',
              'no_validation_policy_change': True}
    output.with_suffix('.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('changed_input', 'manifest_bound_originals',
                                            'packet_bytes', 'read_source_bytes', 'query_and_packet_seconds')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('index', 'packet'))
    parser.add_argument('--run', required=True)
    parser.add_argument('--path')
    parser.add_argument('--out')
    args = parser.parse_args()
    if args.action == 'index':
        index(pathlib.Path(args.run))
    else:
        packet(pathlib.Path(args.run), args.path, pathlib.Path(args.out))
