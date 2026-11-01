"""Compiler-native callgraph replay, including implicit lifecycle calls."""
import argparse
import concurrent.futures
import hashlib
import json
import os
import pathlib
import re
import shlex
import subprocess
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()


def parse_dump(text):
    # First pre-optimization symbol table; retain ABI names rather than demangling IDs.
    section = text.partition('Initial Symbol table:')[2]
    if not section:
        raise ValueError('Unknown GCC cgraph format: initial symbol table missing')
    section = section.split('Removing unused symbols:')[0].split('Reclaimed Symbol table:')[0]
    records = {}
    current = None
    for line in section.splitlines():
        match = re.match(r'^(\S.*?)/(\d+) \((.*)\)(?: @.*)?$', line)
        if match:
            name, number, demangled = match.groups()
            current = {'name': name, 'number': number, 'demangled': demangled,
                       'calls': [], 'references': [], 'indirect': [], 'definition': False}
            records[number] = current
        elif current is not None:
            if line.startswith('  Type:'):
                current['type'] = line.strip()
                current['definition'] = 'definition' in line
            elif line.startswith('  Visibility:'):
                current['visibility'] = line.strip()
            elif line.startswith('  Calls:'):
                current['calls'] += re.findall(r'([^\s()/]+)/(\d+)', line.split(':', 1)[1])
            elif line.startswith('  References:'):
                current['references'] += re.findall(r'([^\s()/]+)/(\d+)', line.split(':', 1)[1])
            elif 'Indirect call' in line or 'Polymorphic' in line:
                current['indirect'].append(line.strip())
    if not records:
        raise ValueError('No GCC symbol records parsed')
    return records


def replay(index, row, scratch, out):
    directory = scratch / f'{index:04d}'
    directory.mkdir(exist_ok=False)
    argv = row.get('arguments') or shlex.split(row['command'])
    argv = list(argv)
    argv[argv.index('-o') + 1] = str(directory / 'unit.o')
    dump = directory / 'unit.cgraph'
    argv.append('-fdump-ipa-cgraph=' + str(dump))
    env = dict(os.environ, TMPDIR=str(directory))
    before = sha(pathlib.Path(row['file']))
    start = time.perf_counter()
    with (directory / 'compile.log').open('w') as log:
        result = subprocess.run(argv, cwd=row['directory'], env=env,
                                stdout=log, stderr=subprocess.STDOUT)
    assert sha(pathlib.Path(row['file'])) == before
    payload = {'source': row['file'], 'argv': argv, 'returncode': result.returncode,
               'source_sha256': before, 'seconds': time.perf_counter() - start,
               'dump': str(dump), 'scratch': str(directory)}
    if result.returncode == 0:
        payload['symbols'] = parse_dump(dump.read_text())
        payload['dump_sha256'] = sha(dump)
    (out / f'{index:04d}.json').write_text(json.dumps(payload) + '\n')
    return {'index': index, 'passed': result.returncode == 0}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', required=True)
    p.add_argument('--index', type=int)
    a = p.parse_args()
    run = pathlib.Path(a.run).resolve()
    rows = json.loads((run / 'compile_commands.json').read_text())
    label = ('probe-' + str(a.index) if a.index is not None else 'all') + '-' + str(time.time_ns())
    scratch = ROOT / 'temp/recovery-work/dependency-graph/full-gcc' / label
    scratch.mkdir(parents=True, exist_ok=False)
    out = run / ('gcc-' + label)
    out.mkdir()
    start = time.perf_counter()
    selected = [(a.index, rows[a.index])] if a.index is not None else list(enumerate(rows))
    completed = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(replay, i, row, scratch, out): i for i, row in selected}
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
            except Exception as exc:
                result = {'index': futures[future], 'passed': False, 'exception': repr(exc)}
            completed.append(result)
            with (out / 'progress.jsonl').open('a') as log:
                log.write(json.dumps(result) + '\n')
    report = {'units': len(selected), 'all_passed': all(x['passed'] for x in completed),
              'failures': [x for x in completed if not x['passed']],
              'seconds': time.perf_counter() - start,
              'compiler': subprocess.check_output(['/usr/bin/c++', '--version'], text=True).splitlines()[0]}
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(report, output=str(out))))
