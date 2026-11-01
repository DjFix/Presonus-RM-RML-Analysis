"""Reproducible, project-specific Docker operations; retain containers and volumes."""
import argparse
import json
import pathlib
import shlex
import subprocess
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = ROOT / 'dependency-graph'
NETWORK = 'dependency-graph-experiment'
IMAGES = {'neo4j': 'neo4j:2026.10.1', 'memgraph': 'memgraph/memgraph-mage:3.13.0'}


def docker(argv):
    command = ['sg', 'docker', '-c', shlex.join(['docker', *argv])]
    logs = BASE / 'runs/docker-operations'
    logs.mkdir(parents=True, exist_ok=True)
    log = logs / (str(time.time_ns()) + '.log')
    start = time.perf_counter()
    with log.open('w') as stream:
        result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT)
    receipt = {'argv': ['docker', *argv], 'returncode': result.returncode,
               'elapsed_seconds': time.perf_counter() - start, 'log': str(log)}
    log.with_suffix('.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt), flush=True)
    print(log.read_text()[-3000:], flush=True)
    if result.returncode:
        raise SystemExit(result.returncode)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('network', 'build-runner', 'start', 'stop',
                                          'restart', 'logs', 'disk',
                                          'images', 'import', 'sqlite-import', 'benchmark', 'case',
                                          'full-load', 'full-check', 'stats', 'inspect'))
    parser.add_argument('--backend', choices=tuple(IMAGES), default='neo4j')
    parser.add_argument('--run', default='dependency-graph/runs/baseline-01')
    parser.add_argument('--label', default='benchmark')
    parser.add_argument('--qualified', action='store_true')
    args = parser.parse_args()
    name = 'dependency-graph-' + args.backend
    run = (ROOT / args.run).resolve()
    assert run.is_relative_to(BASE / 'runs')
    if args.action == 'network':
        docker(['network', 'create', NETWORK])
    elif args.action == 'images':
        docker(['image', 'inspect', *IMAGES.values(), 'dependency-graph-runner:01', 'python:3.12-slim'])
    elif args.action == 'build-runner':
        docker(['build', '-t', 'dependency-graph-runner:01', str(BASE)])
    elif args.action == 'start':
        command = ['run', '-d', '--name', name, '--network', NETWORK,
                   ('--memory=10g' if args.backend == 'memgraph' else '--memory=6g'), '--cpus=2', '-v', name + '-data:' + (
                       '/data' if args.backend == 'neo4j' else '/var/lib/memgraph')]
        if args.backend == 'neo4j':
            command += ['-p', '127.0.0.1:17687:7687', '-p', '127.0.0.1:17474:7474',
                        '-e', 'NEO4J_AUTH=none',
                        '-e', 'NEO4J_server_memory_heap_initial__size=512m',
                        '-e', 'NEO4J_server_memory_heap_max__size=2g',
                        '-e', 'NEO4J_server_memory_pagecache_size=2g', IMAGES[args.backend]]
        else:
            command += ['-p', '127.0.0.1:27687:7687', IMAGES[args.backend],
                        '--memory-limit=8192', '--storage-mode=IN_MEMORY_TRANSACTIONAL']
        docker(command)
    elif args.action in ('stop', 'inspect', 'restart', 'logs'):
        docker([args.action, name])
    elif args.action == 'disk':
        docker(['exec', name, 'du', '-sb', '/data' if args.backend == 'neo4j' else '/var/lib/memgraph'])
    elif args.action == 'stats':
        docker(['stats', '--no-stream', '--format', '{{json .}}', name])
    else:
        script = {'import': 'import_bolt.py', 'sqlite-import': 'import_sqlite.py',
                  'benchmark': 'benchmark_backends.py', 'case': 'case_last_cycle.py',
                  'full-load': 'load_full_graph.py', 'full-check': 'check_full_graph.py'}[args.action]
        command = ['run', '--name', name + '-' + args.action + '-' + str(time.time_ns()),
                   '--network', NETWORK, '--memory=2g', '--cpus=2',
                   '-v', str(ROOT) + ':/workspace:ro',
                   '-v', str(run) + ':/workspace/' + str(run.relative_to(ROOT)) + ':rw',
                   '--user', '1000:1000', 'dependency-graph-runner:01',
                   'dependency-graph/' + script, '--run', str(run.relative_to(ROOT))]
        if args.action == 'sqlite-import':
            command += ['--integer-keys']
        else:
            command += ['--host', name, '--backend', args.backend]
        if args.action == 'benchmark':
            command += ['--port', '7687', '--out', str(run.relative_to(ROOT) / (
                args.backend + '-' + args.label + '.json'))]
        if args.action == 'full-load' and args.qualified:
            command += ['--qualified']
        docker(command)


if __name__ == '__main__':
    main()
