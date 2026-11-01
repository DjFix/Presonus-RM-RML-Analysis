"""Control only the project-local experimental Neo4j distribution."""
import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import tarfile
import time

BASE = pathlib.Path(__file__).resolve().parent
RUNTIME = BASE / 'runtime'
HOME = RUNTIME / 'neo4j-community-2026.10.1'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'help-import', 'import', 'start', 'stop'))
    parser.add_argument('--run')
    args = parser.parse_args()
    if args.action == 'prepare':
        archive = RUNTIME / 'downloads/neo4j-community-2026.10.1-unix.tar.gz'
        checksum = archive.with_name(archive.name + '.sha256').read_text().split()[0]
        assert hashlib.file_digest(archive.open('rb'), 'sha256').hexdigest() == checksum
        assert not HOME.exists(), 'Do not overwrite an existing installation'
        with tarfile.open(archive) as tar:
            tar.extractall(RUNTIME, filter='data')
        config = HOME / 'conf/neo4j.conf'
        with config.open('a') as stream:
            stream.write('''
# Isolated dependency graph experiment, loopback-only ports.
server.default_listen_address=127.0.0.1
server.bolt.listen_address=127.0.0.1:17687
server.http.listen_address=127.0.0.1:17474
server.https.enabled=false
dbms.security.auth_enabled=false
server.memory.heap.initial_size=512m
server.memory.heap.max_size=1g
server.memory.pagecache.size=1g
''')
        (RUNTIME / 'distribution.json').write_text(json.dumps({
            'neo4j_sha256': checksum,
            'java_archive_sha256': hashlib.file_digest(
                (RUNTIME / 'downloads/java21.tar.gz').open('rb'), 'sha256').hexdigest(),
            'installation': str(HOME)}, indent=2) + '\n')
        return
    java = next(RUNTIME.glob('jdk*-jre'))
    scratch = BASE.parent / 'temp/recovery-work/dependency-graph'
    scratch.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, JAVA_HOME=str(java), NEO4J_HOME=str(HOME),
               TMPDIR=str(scratch), JAVA_TOOL_OPTIONS='-Djava.io.tmpdir=' + str(scratch))
    commands = {
        'help-import': [str(HOME / 'bin/neo4j-admin'), 'database', 'import', 'full', '--help'],
        'start': [str(HOME / 'bin/neo4j'), 'start'],
        'stop': [str(HOME / 'bin/neo4j'), 'stop'],
    }
    if args.action == 'import':
        run = pathlib.Path(args.run).resolve()
        assert run.is_relative_to(BASE / 'runs')
        commands['import'] = [str(HOME / 'bin/neo4j-admin'), 'database', 'import', 'full',
                              '--nodes=Artifact=' + str(run / 'neo4j-nodes.csv'),
                              '--relationships=' + str(run / 'neo4j-edges.csv'),
                              '--threads=2', '--max-off-heap-memory=1G',
                              '--report-file=' + str(run / 'neo4j-import.report'), 'neo4j']
    command = commands[args.action]
    stamp = time.time_ns()
    log = RUNTIME / f'{args.action}-{stamp}.log'
    start = time.perf_counter()
    with log.open('w') as stream:
        result = subprocess.run(command, env=env, cwd=RUNTIME, stdout=stream,
                                stderr=subprocess.STDOUT)
    receipt = {'argv': command, 'elapsed_seconds': time.perf_counter() - start,
               'returncode': result.returncode, 'log': str(log)}
    log.with_suffix('.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))
    if result.returncode:
        print(log.read_text()[-6000:])
        raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
