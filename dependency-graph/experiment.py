"""Read-only inputs, isolated graph output. Never used for readiness admission."""
import argparse
import csv
import hashlib
import json
import pathlib
import shlex
import sqlite3
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'uc-library/tools/registry'))
import adapter


def sha(path):
    return hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()


def dependencies(text):
    """GCC make dependency syntax: escaped whitespace and line continuations."""
    text = text.replace('\\\n', '')
    target, sep, body = text.partition(': ')
    if not sep:
        raise ValueError('Missing dependency rule')
    return shlex.split(target), shlex.split(body)


class Graph:
    def __init__(self, path):
        self.c = sqlite3.connect(path)
        self.c.executescript('''
        CREATE TABLE nodes(id TEXT PRIMARY KEY, kind TEXT, label TEXT, metadata TEXT);
        CREATE TABLE edges(src TEXT REFERENCES nodes(id), dst TEXT REFERENCES nodes(id),
          kind TEXT, evidence TEXT, PRIMARY KEY(src,dst,kind,evidence));
        CREATE INDEX reverse_edges ON edges(dst,kind,src);
        CREATE TABLE inputs(path TEXT PRIMARY KEY, sha256 TEXT);
        ''')

    def node(self, key, kind, label, metadata=None):
        self.c.execute('INSERT OR IGNORE INTO nodes VALUES(?,?,?,?)',
                       (key, kind, label, json.dumps(metadata or {}, sort_keys=True)))
        return key

    def edge(self, src, dst, kind, evidence):
        self.c.execute('INSERT OR IGNORE INTO edges VALUES(?,?,?,?)',
                       (src, dst, kind, evidence))

    def capture(self, path):
        digest = sha(path)
        self.c.execute('INSERT OR IGNORE INTO inputs VALUES(?,?)', (str(path), digest))
        return digest

    def file(self, path):
        path = pathlib.Path(path).resolve()
        label = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
        return self.node('file:' + label, 'file', label)


def impact(c, key, kinds):
    marks = ','.join('?' for _ in kinds)
    return c.execute(f'''WITH RECURSIVE affected(id) AS (
      SELECT ? UNION SELECT e.src FROM edges e JOIN affected a ON e.dst=a.id
      WHERE e.kind IN ({marks}))
      SELECT n.id,n.kind,n.label FROM affected a JOIN nodes n ON n.id=a.id
      ORDER BY n.kind,n.label''', (key, *kinds)).fetchall()


def build(args):
    out = pathlib.Path(args.out).resolve()
    if not out.is_relative_to(ROOT / 'dependency-graph'):
        raise ValueError('Outputs must remain under dependency-graph/')
    out.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter()
    g = Graph(out / 'graph.sqlite')
    library = ROOT / 'uc-library'
    build_dir = (ROOT / args.build).resolve()
    provenance = {}
    with adapter.snapshot(library, args.registry_db) as snap:
        provenance = snap.provenance()
        # Consistent SQLite backup, including committed WAL contents.
        backup = sqlite3.connect(out / 'registry-snapshot.sqlite')
        snap.c.backup(backup)
        backup.close()
        for status in ('ready', 'pending'):
            for entry in snap.iter_records(status):
                key = 'symbol:' + entry['original_elf_sha256'] + ':' + entry['mangled']
                g.node(key, 'symbol', entry['mangled'], {
                    'elf': entry['original_elf_sha256'], 'status': status})
                for field in ('sources', 'repository_sources'):
                    for path, digest in entry.get(field, {}).items():
                        base = library if field == 'sources' else ROOT
                        g.edge(key, g.file(base / path), 'proof_binding',
                               json.dumps({'field': field, 'digest': digest}, sort_keys=True))
                if entry.get('validation'):
                    g.edge(key, g.file(library / entry['validation']), 'validation_binding',
                           str(entry.get('validation_sha256', 'unrecorded')))
    commands_path = build_dir / 'compile_commands.json'
    g.capture(commands_path)
    commands = json.loads(commands_path.read_text())
    missing = []
    production = set()
    for command in commands:
        directory = pathlib.Path(command['directory'])
        argv = command.get('arguments') or shlex.split(command['command'])
        source = pathlib.Path(command['file'])
        source = source if source.is_absolute() else directory / source
        if '-o' not in argv:
            missing.append({'source': str(source), 'reason': 'no -o'})
            continue
        obj = directory / argv[argv.index('-o') + 1]
        objkey = g.file(obj)
        g.edge(objkey, g.file(source), 'compiles', str(commands_path))
        if source.resolve().is_relative_to(library / 'src'):
            production.add(objkey)
        dep = pathlib.Path(str(obj) + '.d')
        if not dep.exists():
            missing.append({'source': str(source), 'reason': 'missing depfile'})
            continue
        g.capture(dep)
        _, paths = dependencies(dep.read_text())
        for path in paths:
            g.edge(objkey, g.file(directory / path), 'compiler_input', str(dep))
    for link in sorted(build_dir.glob('CMakeFiles/*/link.txt')):
        g.capture(link)
        argv = shlex.split(link.read_text())
        # Recognize explicit object/archive operands; never execute link commands.
        if '-o' in argv:
            output = argv[argv.index('-o') + 1]
        elif argv and pathlib.Path(argv[0]).name in ('ar', 'gcc-ar', 'llvm-ar'):
            output = next((x for x in argv[1:] if x.endswith('.a')), None)
        else:
            output = None
        if output:
            target = g.file(build_dir / output)
            for token in argv:
                if token != output and token.endswith(('.o', '.a')):
                    g.edge(target, g.file(build_dir / token), 'link_input', str(link))
    g.capture(pathlib.Path(__file__))
    g.capture(ROOT / 'uc-library/tools/registry/adapter.py')
    for path, digest in g.c.execute('SELECT path,sha256 FROM inputs').fetchall():
        if sha(pathlib.Path(path)) != digest:
            raise ValueError('Input changed during extraction: ' + path)
    g.c.commit()
    scenarios = {}
    for label in ('uc-library/include/surface_panel/ControlHelpers.hpp',
                  'uc-library/src/Presonus/Panel/ControlRegistrarAccess.cpp',
                  'uc-library/cmake/ProductionSourceGroups.cmake'):
        # Resolve actual header casing/location from graph rather than assume it.
        candidates = g.c.execute('SELECT id,label FROM nodes WHERE label=? OR label LIKE ?',
                                 (label, '%/' + pathlib.Path(label).name)).fetchall()
        for key, actual in candidates:
            code = impact(g.c, key, ('compiler_input', 'compiles', 'link_input'))
            proofs = impact(g.c, key, ('proof_binding', 'validation_binding'))
            scenarios[actual] = {'build_affected': code, 'proof_affected': proofs,
                                'production_objects': sum(r[0] in production for r in code)}
    (out / 'scenarios.json').write_text(json.dumps(scenarios, indent=2) + '\n')
    for table in ('nodes', 'edges'):
        with (out / (table + '.csv')).open('w') as stream:
            writer = csv.writer(stream)
            cursor = g.c.execute('SELECT * FROM ' + table + ' ORDER BY 1,2,3')
            writer.writerow([d[0] for d in cursor.description])
            writer.writerows(cursor)
    report = {'registry': provenance, 'snapshot_sha256': sha(out / 'registry-snapshot.sqlite'),
              'elapsed_seconds': time.perf_counter() - start,
              'nodes': g.c.execute('SELECT count(*) FROM nodes').fetchone()[0],
              'edges_by_kind': dict(g.c.execute('SELECT kind,count(*) FROM edges GROUP BY kind')),
              'compile_commands': len(commands), 'production_objects': len(production),
              'missing_dependencies': missing, 'admission_authority': False,
              'limitations': ['No call/type/virtual-dispatch graph',
                             'Compiler dependencies describe observed build, not semantic independence',
                             'Proof bindings are provenance, not proven implementation dependencies',
                             'No tests may be skipped based on this experiment',
                             'No Neo4j runtime benchmark executed']}
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('nodes', 'edges_by_kind', 'elapsed_seconds')}))
    g.c.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry-db')
    parser.add_argument('--build', default='temp/core-upstream/root-integration-01')
    parser.add_argument('--out', required=True)
    build(parser.parse_args())
