"""Isolated real selector/slicer benchmark; never launches reconstruction workers.

This deliberately measures builder and packet validation costs, excluding host
refresh/enrichment/claim coordination. It uses a copied unique-work database,
current registry records, and read-only production source/native graph inputs.
The production Memgraph is queried, never modified. All Docker root mounts are
read-only except the new benchmark output tree. No dispatch is published.
"""
import argparse
import concurrent.futures
import fcntl
import importlib.util
import json
import os
import pathlib
import re
import shlex
import sqlite3
import subprocess
import sys
import threading
import time

from context_runtime import ContextError, guard, inside, sha
from context_resources import choose_limits
from dedup_index import connect
from dedup_work import claim
from context_batch import Environment, capture_inputs, freeze_snapshot
from memgraph_endpoint import memgraph_uri

ROOT = pathlib.Path(__file__).resolve().parents[1]


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def backup(source, destination):
    with sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True) as src:
        with sqlite3.connect(destination) as dst:
            src.backup(dst)


def normalize(value, prefixes):
    """Normalize run-local paths and genuinely run-specific claim identities only."""
    if isinstance(value, dict):
        skip = set()
        if 'work_item_id' in value and 'claim_id' in value:
            skip.update(('claim_id', 'claim_owner', 'claim_packet', 'database'))
        if 'packet_sha256' in value and 'generation_sha256' in value and 'task_id' in value:
            # Recomputed from independently compared bound artifacts below.
            skip.update(('packet_sha256', 'task_sha256'))
        return {normalize(k, prefixes): normalize(v, prefixes) for k, v in value.items() if k not in skip}
    if isinstance(value, list):
        return [normalize(v, prefixes) for v in value]
    if isinstance(value, str):
        for prefix in prefixes:
            value = value.replace(prefix, '$RUN')
        return value
    return value


def unordered_key(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def canonical_packet(value, prefixes):
    """Only known nonsemantic collections are multisets; never discard duplicates."""
    packet = normalize(value, prefixes)
    packet['unknowns'] = sorted(packet['unknowns'], key=unordered_key)
    packet['slice_translation_units'] = sorted(packet['slice_translation_units'])
    packet['inclusion_reasons'] = {key:sorted(reasons)
                                   for key,reasons in packet['inclusion_reasons'].items()}
    return packet


def canonical_context_markdown(text):
    """Normalize only the generated Unknowns JSON; preserve all other text/order."""
    marker = '\n## Unknowns\n\n'
    head, tail = text.split(marker, 1)
    unknowns, end = json.JSONDecoder().raw_decode(tail)
    if not isinstance(unknowns, list):
        raise ContextError('Context Unknowns must be a JSON list')
    return head+marker+json.dumps(sorted(unknowns,key=unordered_key),sort_keys=True)+tail[end:]


def resource_summary(samples):
    """Sampled container aggregates, not exact peaks or remote graph usage."""
    memory_peak, cpu_peak = 0, 0.0
    factors = {'B':1, 'kB':1000, 'KB':1000, 'KiB':1024, 'MB':1000**2,
               'MiB':1024**2, 'GB':1000**3, 'GiB':1024**3}
    for sample in samples:
        memory, cpu = 0, 0.0
        for line in sample['stdout'].splitlines():
            try:
                row = json.loads(line)
                cpu += float(row.get('CPUPerc', '0%').rstrip('%'))
                match = re.fullmatch(r'([0-9.]+)\s*([A-Za-z]+)', row.get('MemUsage', '').split('/')[0].strip())
                if match:
                    memory += int(float(match[1])*factors[match[2]])
            except (ValueError, TypeError, KeyError):
                continue
        memory_peak, cpu_peak = max(memory_peak, memory), max(cpu_peak, cpu)
    return {'sampled_peak_total_container_memory_bytes':memory_peak,
            'sampled_peak_total_container_cpu_percent':cpu_peak,
            'samples':len(samples),
            'scope':'Docker stats sampling; may miss short peaks; excludes remote graph and host coordinator'}


class Harness:
    def __init__(self, output):
        self.output = output
        self.receipts = []
        self.mutex = threading.Lock()
        self.counter = 0
        self.containers = []
        self.active_containers = []

    def docker(self, arguments, phase, timeout_seconds=None):
        with self.mutex:
            index = self.counter
            self.counter += 1
        argv = ['sg', 'docker', '-c', shlex.join(['docker', *arguments])]
        started = time.perf_counter()
        with (self.output / f'{index:04d}-{phase}.log').open('x') as log:
            try:
                result = subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT, cwd=ROOT, timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                log.write('Optional telemetry timeout; output retained.\n')
                result = subprocess.CompletedProcess(argv, 124)
                if '--name' in arguments:
                    name = arguments[arguments.index('--name')+1]
                    cleanup = ['sg','docker','-c',shlex.join(['docker','stop','-t','1',name])]
                    try:
                        subprocess.run(cleanup,stdout=log,stderr=subprocess.STDOUT,timeout=5)
                    except subprocess.TimeoutExpired:
                        log.write('Telemetry container stop timed out; inspect retained handle '+name+'\n')
        metrics = []
        for line in (self.output / f'{index:04d}-{phase}.log').read_text().splitlines():
            try:
                value = json.loads(line)
                if isinstance(value, dict) and 'graph_metrics' in value:
                    metrics.append(value['graph_metrics'])
            except (ValueError, TypeError):
                pass
        receipt = {'argv': argv, 'phase': phase, 'seconds': time.perf_counter()-started,
                   'returncode': result.returncode, 'graph_metrics':metrics,
                   'log':str(self.output / f'{index:04d}-{phase}.log')}
        with self.mutex:
            self.receipts.append(receipt)
            with (self.output/'commands.jsonl').open('a') as stream:
                stream.write(json.dumps(receipt)+'\n')
        if result.returncode:
            raise ContextError(f'Benchmark command failed; see {index:04d}-{phase}.log')
        return receipt

    def mounts(self, runner):
        args = ['--network=' + ('dependency-graph-experiment' if runner else 'none'),
                '--user=1000:1000', '--workdir='+str(ROOT),
                '-e', 'DEPENDENCY_GRAPH_ROOT='+str(ROOT),
                '-e', 'TMPDIR='+str(self.output),
                '-e', 'SQLITE_TMPDIR='+str(self.output),
                '-v', f'{ROOT}:{ROOT}:ro',
                '-v', f'{self.output}:{self.output}:rw',
                '-v', f'{self.output}/DEDUP_ACTIVE.json:{ROOT}/dependency-graph/DEDUP_ACTIVE.json:ro']
        # Overlay the POINTER, not the production main DB file: an old canonical
        # -wal sidecar must never attach to a different copied main database.
        args += ['-v', f'{self.output}/REGISTRY_ACTIVE.json:{ROOT}/uc-library/validation/registry-sqlite/ACTIVE.json:ro',
                 '-v', f'{self.output}/registry.sqlite:{self.output}/registry.sqlite:ro']
        if not runner:
            for directory in ('/usr/include/openssl', '/usr/include/x86_64-linux-gnu/openssl'):
                args += ['-v', f'{directory}:{directory}:ro']
        return args

    def persistent(self, runner):
        name = f'context-benchmark-{time.time_ns()}'
        image = 'dependency-graph-runner:01' if runner else 'dependency-graph-analysis:01'
        self.docker(['run', '-d', '--name', name, *self.mounts(runner),
                     '--entrypoint', '/bin/sh', image,
                     '-c', 'while :; do sleep 60; done'], 'environment')
        self.containers.append(name)
        self.active_containers.append(name)
        return name

    def execute(self, args, phase, runner=True, container=None, timeout_seconds=None):
        if container:
            return self.docker(['exec', container, 'python3', *map(str, args)], phase, timeout_seconds)
        image = 'dependency-graph-runner:01' if runner else 'dependency-graph-analysis:01'
        name = f'context-benchmark-stage-{time.time_ns()}'
        self.active_containers.append(name)
        try:
            return self.docker(['run', '--name', name,
                                *self.mounts(runner), image, *map(str, args)], phase, timeout_seconds)
        finally:
            self.active_containers.remove(name)

    def observe_storage(self, container=None):
        # SHOW is read-only. Failed/unavailable optional telemetry is evidence,
        # never a prerequisite for packet preparation or benchmark admission.
        uri = memgraph_uri(ROOT)
        code = ("import json,time; from neo4j import GraphDatabase; "
                "d=GraphDatabase.driver("+repr(uri)+",auth=None,connection_timeout=5,connection_acquisition_timeout=5,max_transaction_retry_time=0); "
                "s=d.session(); "
                "rows=s.run('SHOW STORAGE INFO').data(); "
                "print(json.dumps({'available':True,'epoch':time.time(),'rows':rows},default=str)); "
                "s.close(); d.close()")
        started = time.perf_counter()
        try:
            receipt = self.execute(['-c', code], 'graph-observation', container=container, timeout_seconds=20)
            lines = pathlib.Path(receipt['log']).read_text().splitlines()
            value = json.loads(lines[-1])
            value['seconds'] = time.perf_counter()-started
            return value
        except Exception as error:
            return {'available':False, 'error':str(error), 'seconds':time.perf_counter()-started}

    def stop(self):
        for name in self.containers:
            self.docker(['stop', '-t', '1', name], 'environment-stop')


class BenchmarkEnvironment(Environment):
    """Actual batch Environment, adding only independent mutable-store overlays."""
    def __init__(self, root, output, harness):
        self.harness = harness
        super().__init__(root, output)

    def command(self, argv, tag):
        argv = list(argv)
        if argv[:3] == ['docker', 'run', '-d']:
            replacements = {
                str(self.root/'dependency-graph/DEDUP_ACTIVE.json'):str(self.output/'DEDUP_ACTIVE.json'),
                str(self.root/'uc-library/validation/registry-sqlite/ACTIVE.json'):str(self.output/'REGISTRY_ACTIVE.json'),
                str(self.output/'registry.sqlite'):str(self.output/'registry.sqlite')}
            # Docker rejects duplicate exact destination mounts. Replace the
            # frozen production pointer's existing mount rather than append a
            # second target; all other snapshot mounts stay byte-for-byte intact.
            for index, token in enumerate(argv[:-1]):
                if token == '-v':
                    target = argv[index+1].split(':')[1]
                    if target in replacements:
                        argv[index+1] = replacements.pop(target)+':'+target+':ro'
            insertion = argv.index('--user')
            additional = []
            for target, source in replacements.items():
                additional += ['-v', source+':'+target+':ro']
            argv[insertion:insertion] = additional
        phase = ('shutdown' if tag.startswith('environment-stop-') else
                 'selection' if tag.startswith('select-') else
                 'finalize' if tag.startswith('finalize-') else
                 'slicing' if tag.startswith('slice-') else
                 'validation' if tag.startswith('validation-') else 'environment')
        self.harness.docker(argv[1:], phase)
        if argv[:3] == ['docker', 'run', '-d']:
            self.harness.active_containers.append(argv[argv.index('--name')+1])


def create_run(output, task_paths, operator, source_db):
    output.mkdir(parents=True, exist_ok=False)
    backup(source_db, output/'dedup.sqlite')
    registry_active = json.loads((ROOT/'uc-library/validation/registry-sqlite/ACTIVE.json').read_text())
    registry_path = pathlib.Path(registry_active['database'].get('absolute_path') or ROOT/registry_active['database']['path'])
    backup(registry_path, output/'registry.sqlite')
    registry_active['database']['absolute_path'] = str(output/'registry.sqlite')
    registry_active['database']['path'] = str((output/'registry.sqlite').relative_to(ROOT))
    write(output/'REGISTRY_ACTIVE.json', registry_active)
    pointer = json.loads((ROOT/'dependency-graph/DEDUP_ACTIVE.json').read_text())
    pointer['database'] = str((output/'dedup.sqlite').relative_to(ROOT))
    write(output/'DEDUP_ACTIVE.json', pointer)
    packets = []
    with connect(output/'dedup.sqlite') as database:
        for index, source in enumerate(task_paths):
            original = json.loads(source.read_text())
            original.update(mode='audit', owned_files=[], objective='Read-only context performance benchmark; no worker launch.')
            original.pop('work_binding', None)
            original.pop('originals', None)
            original.pop('registry_guard', None)
            task = operator.enrich(original)
            # Only the independent TEST COPY is reset to a plan-able baseline.
            # History/results are retained. Existing production claims are never changed.
            native_id = json.loads(source.read_text()).get('work_binding', {}).get('work_item_id')
            if not native_id:
                oldpacket = source.parent.parent/(source.stem+'-packet')/'request.json'
                native_id = json.loads(oldpacket.read_text())['work_binding']['work_item_id']
            row = database.execute('SELECT status FROM reconstruction_work_items WHERE id=?', (native_id,)).fetchone()
            if not row:
                raise ContextError('Benchmark identity missing from copied work index')
            if database.execute('SELECT 1 FROM work_claims WHERE work_item_id=? AND state="active"', (native_id,)).fetchone():
                raise ContextError('Active source claim: benchmark refuses to steal even in its copy')
            database.execute('UPDATE reconstruction_work_items SET status="pending" WHERE id=?', (native_id,))
            database.commit()
            packet = output/f'packet-{index:03d}'
            packet.mkdir()
            relative = str(packet.relative_to(ROOT))
            result = claim(database, task, task['task_id'], relative)
            if not result['acquired']:
                raise ContextError('Independent benchmark claim failed')
            task['work_binding'] = dict(result['plan'], database=pointer['database'])
            write(packet/'request.json', task)
            packets.append(relative)
    write(output/'isolation.json', {
        'source_database': str(source_db.relative_to(ROOT)), 'source_database_sha256': sha(source_db),
        'test_database': pointer['database'], 'registry_copy': str((output/'registry.sqlite').relative_to(ROOT)),
        'test_only_baseline': 'Selected completed work reopened only in independent copy; history retained; new claims via real planner',
        'production_claims_changed': False, 'production_readiness_changed': False,
        'no_dispatch_published': True, 'source_tasks': {str(p.relative_to(ROOT)): sha(p) for p in task_paths}})
    return packets


def run_one(output, paths, mode, jobs, operator, source_db):
    isolation_start = time.perf_counter()
    packets = create_run(output, paths, operator, source_db)
    isolation_seconds = time.perf_counter()-isolation_start
    harness = Harness(output)
    limits = choose_limits(jobs, len(packets))
    graph_before = harness.observe_storage()
    started = time.perf_counter()
    errors = []
    runner = analysis = None
    environment = None
    snapshot_seconds = 0.0
    graph_slots = threading.BoundedSemaphore(limits['selection_jobs'])
    samples = []
    stopped = threading.Event()

    def sample():
        while not stopped.wait(2):
            names = list(harness.active_containers)
            if not names:
                continue
            args = ['sg', 'docker', '-c', shlex.join(['docker', 'stats', '--no-stream', '--format', '{{json .}}', *names])]
            result = subprocess.run(args, capture_output=True, text=True)
            samples.append({'epoch': time.time(), 'stdout': result.stdout, 'returncode': result.returncode})

    observer = threading.Thread(target=sample, daemon=True)
    observer.start()
    try:
        if mode == 'persistent':
            snapshot_started = time.perf_counter()
            environment = BenchmarkEnvironment(ROOT, output, harness)
            environment.pin_images()
            frozen = capture_inputs(ROOT, operator, [str(p.relative_to(ROOT)) for p in paths])
            requests = [json.loads((ROOT/p/'request.json').read_text()) for p in packets]
            snapshot = freeze_snapshot(ROOT, output, frozen, requests)
            write(output/'snapshot-benchmark.json', {
                'seconds':time.perf_counter()-snapshot_started,
                'bytes':sum((output/'snapshot'/p).stat().st_size for p in snapshot['files']),
                'files':len(snapshot['files']), 'producer':'context_batch.freeze_snapshot',
                'manifest_sha256':sha(output/'SNAPSHOT.json')})
            snapshot_seconds = time.perf_counter()-snapshot_started
            environment.start()
        slicing_slots = threading.BoundedSemaphore(limits['slicing_jobs'])
        def build(packet):
            with graph_slots:
                if environment:
                    environment.selector('prepare', [packet], 'select-'+pathlib.Path(packet).name)
                else:
                    harness.execute([ROOT/'dependency-graph/context_selector.py', 'prepare', '--out', packet], 'selection')
            with slicing_slots:
                if environment:
                    environment.slice(packet, 'slice-'+pathlib.Path(packet).name)
                else:
                    harness.execute([ROOT/'dependency-graph/context_slices.py', ROOT/packet], 'slicing', False)
            with graph_slots:
                if environment:
                    environment.selector('finalize', [packet], 'finalize-'+pathlib.Path(packet).name)
                else:
                    harness.execute([ROOT/'dependency-graph/context_selector.py', 'finalize', '--out', packet], 'finalize')
        with concurrent.futures.ThreadPoolExecutor(max_workers=limits['builder_jobs'] if mode=='persistent' else 1) as pool:
            list(pool.map(build, packets))
        if mode == 'persistent':
            ast_bindings = []
            snapshot = json.loads((output/'SNAPSHOT.json').read_text())
            for packet in packets:
                slices = json.loads((ROOT/packet/'source-slices.json').read_text())
                for function, item in slices['functions'].items():
                    expected = snapshot['files'].get(item['path'])
                    if expected is None or item['source_sha256'] != expected:
                        raise ContextError('AST sliced an input not matching immutable snapshot: '+item['path'])
                    ast_bindings.append({'packet':packet, 'function':function, 'path':item['path'], 'sha256':expected})
            write(output/'ast-snapshot-bindings.json', ast_bindings)
            if not ast_bindings:
                raise ContextError('Benchmark has no observed AST bodies; use source-mapped tasks')
            environment.selector('validate', packets, 'validation-all')
        else:
            for packet in packets:
                harness.execute([ROOT/'dependency-graph/context_selector.py', 'validate', '--out', packet], 'validation')
    except Exception as exc:
        errors.append(str(exc))
    processing_seconds = time.perf_counter()-started
    observer_stop_started = time.perf_counter()
    stopped.set()
    observer.join(timeout=5)
    observer_finalize_seconds = time.perf_counter()-observer_stop_started
    graph_after = harness.observe_storage(environment.names['runner'] if environment else None)
    shutdown_started = time.perf_counter()
    try:
        if environment:
            environment.close()
    except Exception as exc:
        errors.append('Environment shutdown: '+str(exc))
    try:
        harness.stop()
    except Exception as exc:
        errors.append('Legacy environment shutdown: '+str(exc))
    shutdown_seconds = time.perf_counter()-shutdown_started
    pipeline_seconds = processing_seconds+shutdown_seconds
    write(output/'resource-samples.json', samples)
    payload = {'mode':mode, 'requested_jobs':jobs, 'limits':limits, 'isolation_seconds':isolation_seconds,
               'builder_validation_wall_seconds':processing_seconds-snapshot_seconds,
               'processing_wall_seconds':processing_seconds,
               'immutable_snapshot_seconds':snapshot_seconds,
               'shutdown_seconds':shutdown_seconds,
               'pipeline_wall_seconds':pipeline_seconds,
               'observation_overhead_seconds':graph_before.get('seconds',0)+graph_after.get('seconds',0)+observer_finalize_seconds,
               'observer_finalize_seconds':observer_finalize_seconds,
               'timing_scope':'Pipeline includes immutable snapshot, actual image/environment startup, builders, validation and actual shutdown. Excludes isolation, optional graph telemetry, observer finalization and final report writes. Concurrent sampling perturbation is not subtracted.',
               'errors':errors, 'packets':packets,
               'resource_summary':resource_summary(samples),
               'graph_storage_observations':{'before':graph_before,'after':graph_after},
               'graph_metrics': {
                   'graph_queries':sum(m.get('graph_queries',0) for r in harness.receipts for m in r.get('graph_metrics',[])),
                   'graph_seconds':sum(m.get('graph_seconds',0) for r in harness.receipts for m in r.get('graph_metrics',[]))},
               'phases': {p:sum(r['seconds'] for r in harness.receipts if r['phase']==p)
                          for p in sorted({r['phase'] for r in harness.receipts})},
               'remote_graph_cpu':'not observed; concurrency and selector query counts are load proxies; optional SHOW STORAGE INFO memory/storage start/end are recorded',
               'scope':'real selector/native/slicer/finalize/full packet validation; excludes host refresh/claim/enrich/publication'}
    write(output/'result.json', payload)
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    parser.add_argument('--tasks', nargs='+', required=True, help='Pre-enriched request.json files or original trial task files')
    parser.add_argument('--jobs', nargs='+', default=['1','4','8','auto'])
    parser.add_argument('--repeats', type=int, default=2)
    args = parser.parse_args()
    output = inside(ROOT, args.out)
    if not output.is_relative_to(ROOT/'temp/recovery-work'):
        raise ContextError('Benchmark output must be new project recovery scratch')
    output.mkdir(parents=True, exist_ok=False)
    task_paths = [inside(ROOT, p) for p in args.tasks]
    spec = importlib.util.spec_from_file_location('benchmark_operator', ROOT/'uc-library/tools/recovery/select_context.py')
    operator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(operator)
    pointer = json.loads((ROOT/'dependency-graph/DEDUP_ACTIVE.json').read_text())
    source_db = inside(ROOT, pointer['database'])
    results = []
    with (ROOT/'dependency-graph/state/context.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_SH)
        active = json.loads((ROOT/'dependency-graph/ACTIVE.json').read_text())
        guard(ROOT, active)
        write(output/'freeze.json', {'active':active, 'benchmark_producer_sha256':sha(pathlib.Path(__file__)),
                                    'tools':{str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'dependency-graph').glob('*.py')},
                                    'normalization_policy':'Run-local paths and exact work-binding claim fields only; context unknowns, inclusion_reasons and slice_translation_units lists are multisets retaining duplicates; CONTEXT.md Unknowns JSON only. Every other body/identity/hash/value/list order retained.',
                                    'cache_policy':'Each run starts new containers and Python processes; persistent mode reuses containers within a run. First run has uncontrolled filesystem/server cache; later repeats are warm-order. No cache flushing and no claim of OS-cache cold.'})
        for repeat in range(args.repeats):
            for mode, jobs in [('legacy','1'), *[('persistent', n) for n in args.jobs]]:
                result = run_one(output/f'{repeat:02d}-{mode}-{jobs}', task_paths, mode, jobs, operator, source_db)
                results.append(result)
                if result['errors']:
                    write(output/'results.json', results)
                    raise ContextError('Benchmark run failed; evidence retained')
        guard(ROOT, active)
        freeze = json.loads((output/'freeze.json').read_text())
        if any(sha(ROOT/path) != digest for path, digest in freeze['tools'].items()):
            write(output/'results.json', results)
            raise ContextError('Producer changed during benchmark; measurements are not comparable')
    baseline = None
    comparisons = []
    for result in results:
        normalized = []
        for packet in result['packets']:
            folder = ROOT/packet
            item = canonical_packet(json.loads((folder/'context.json').read_text()), [str(folder),packet,str(folder.parent),str(folder.parent.relative_to(ROOT))])
            # Native context evidence contains output paths; compare all values after documented normalization.
            artifacts = {}
            context = json.loads((folder/'context.json').read_text())
            binding = context['work_binding']
            prefixes = [str(folder), packet, str(folder.parent), str(folder.parent.relative_to(ROOT))]
            replacements = {binding['claim_id']: '$CLAIM', binding['database']: '$DATABASE',
                            binding['claim_packet']: '$PACKET'}
            for name in context['packet_sha256']:
                bound = folder/name
                content = bound.read_text()
                if name.endswith('.json'):
                    artifacts[name] = normalize(json.loads(content), prefixes)
                else:
                    for old, new in replacements.items():
                        content = content.replace(old, new)
                    artifacts[name] = normalize(content, prefixes)
                    if name == 'CONTEXT.md':
                        artifacts[name] = canonical_context_markdown(artifacts[name])
            normalized.append({'context':item, 'bound_artifacts':artifacts})
        if baseline is None:
            baseline = normalized
        comparisons.append({'run':str(pathlib.Path(result['packets'][0]).parent), 'mandatory_context_equal':normalized==baseline})
    write(output/'equivalence.json', comparisons)
    write(output/'results.json', results)
    if not all(c['mandatory_context_equal'] for c in comparisons):
        raise ContextError('Mandatory packet context differs; inspect equivalence results')
    print(output/'results.json')


if __name__ == '__main__':
    try:
        main()
    except (ContextError, ValueError, KeyError) as exc:
        raise SystemExit('BENCHMARK BLOCKED: '+str(exc))
