"""Measure real grouped preparation without spawning workers or copying databases.

--select-audit builds an explicitly read-only workload from the current SQLite
catalog, excluding compiled results, live claims, retained reservations and Core.
This is a preparation benchmark, not an implementation-eligibility/readiness claim.
--tasks instead accepts operator-reviewed reconstruction manifests unchanged.
All ordinary claim, graph, native, slicing and publication gates run in both cases.
"""
import argparse
from collections import defaultdict
import datetime
import fcntl
import importlib.util
import json
from pathlib import Path
import sqlite3
import time

from context_runtime import ContextError, inside, sha
from context_batch import DEFAULT_SNAPSHOT_COPY_BYTES

ROOT = Path(__file__).resolve().parents[1]


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def readonly(path):
    connection = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def select_audit(output, prepared, groups, per_group):
    started = time.perf_counter()
    from context_batch import validate_tasks
    registry_pointer = json.loads((ROOT/'uc-library/validation/registry-sqlite/ACTIVE.json').read_text())
    registry_path = Path(registry_pointer['database'].get('absolute_path') or ROOT/registry_pointer['database']['path'])
    pointer = json.loads((ROOT/'dependency-graph/DEDUP_ACTIVE.json').read_text())
    native_pointer = json.loads((ROOT/'dependency-graph/NATIVE_ACTIVE.json').read_text())
    registry, work, native = readonly(registry_path), readonly(inside(ROOT,pointer['database'])), readonly(inside(ROOT,native_pointer['database']))
    try:
        # Current canonical catalog/status/history is the starting point.
        rows = registry.execute('''SELECT s.*,t.state AS task_state,t.notes,t.revision FROM catalog_symbols s
            JOIN catalog_tasks t ON t.anchor=s.anchor
            LEFT JOIN records r ON r.elf=s.elf AND r.mangled=s.mangled
            WHERE s.kind='STT_FUNC' AND s.demangled LIKE 'Presonus::%' AND s.size>0
              AND r.elf IS NULL AND t.state='todo'
            ORDER BY s.size,s.demangled,s.elf,s.address''').fetchall()
        scopes = defaultdict(list)
        # One join, indexed in memory by catalog anchor. Do not repeat a work-kind
        # scan for every catalog row or modify the operational DB for a benchmark.
        available = defaultdict(list)
        for candidate in work.execute("""SELECT w.id,o.native_id,o.catalog_anchor FROM reconstruction_work_items w
            JOIN work_item_members m ON m.work_item_id=w.id
            JOIN symbol_occurrences o ON o.id=m.occurrence_id
            WHERE w.status='todo' AND w.work_kind='reconstruct' AND o.strategy!='external_source'
              AND (SELECT count(*) FROM work_item_members m2 WHERE m2.work_item_id=w.id)=1
              AND NOT EXISTS(SELECT 1 FROM work_claims c WHERE c.work_item_id=w.id AND c.state='active')
              AND NOT EXISTS(SELECT 1 FROM carryover_reservations r WHERE r.occurrence_id=o.id)"""):
            available[candidate['catalog_anchor']].append(candidate)
        seen = set()
        for row in rows:
            if row['notes'].strip():
                continue  # Notes require explicit review; never silently erase them.
            candidates = available[row['anchor']]
            if len(candidates) != 1 or candidates[0]['id'] in seen:
                continue
            candidate = candidates[0]
            body = native.execute('SELECT payload FROM bodies WHERE id=?',(candidate['native_id'],)).fetchone()
            if not body or not json.loads(body[0]).get('instructions'):
                continue
            head = row['demangled'].split('(',1)[0]
            if '::' not in head:
                continue
            scope = head.rsplit('::',1)[0]
            if '<' in scope or ' ' in scope:
                continue
            seen.add(candidate['id'])
            scopes[scope].append((dict(row), candidate['id']))
        eligible = [(scope, values) for scope, values in scopes.items() if len(values)>=per_group]
        # Mix scopes; retain explicit size distribution rather than claiming random sampling.
        eligible.sort(key=lambda item: (sum(row['size'] for row,_ in item[1][:per_group]), item[0]))
        if len(eligible)<groups:
            raise ContextError('Not enough distinct eligible scopes for exact benchmark shape')
        tasks, grouped, history = [], [], []
        (output/'tasks').mkdir()
        for group_index, (scope, values) in enumerate(eligible[:groups]):
            packets = []
            for index, (row, work_id) in enumerate(values[:per_group]):
                ident = f'prepbench_g{group_index:02d}_s{index:02d}'
                task = {'task_id':ident,'mode':'audit','work_kind':'reconstruct','namespace':scope,
                        'objective':'Read-only preparation measurement: inspect exact native/source context; no implementation or worker launch.',
                        'owned_files':[], 'targets':[{'original_elf_sha256':row['elf'],'mangled':row['mangled'],
                            'anchor':row['anchor'],'address':row['address'],'size':row['size']}],
                        'prior_history':{'state':row['task_state'],'revision':row['revision'],'notes':row['notes']}}
                path = output/'tasks'/f'{ident}.json'
                write(path,task); tasks.append(str(path.relative_to(ROOT)))
                packets.append(str((prepared/'packets'/ident).relative_to(ROOT)))
                history.append({'task':ident,'work_item_id':work_id,'scope':scope,'original':row})
            grouped.append({'task_name':f'prepbench_group{group_index:02d}','scope_reason':scope+' read-only context measurement',
                            'packets':packets,'execution_order':packets})
        validate_tasks([json.loads((ROOT/p).read_text()) for p in tasks],grouped)
        manifest = output/'TASKS.json'
        write(manifest,{'tasks':tasks,'groups':grouped})
        write(output/'SELECTION.json',{'seconds':time.perf_counter()-started,'mode':'audit-only; no reconstruction eligibility claim',
              'selection':'Current catalog todo, no record, no notes requiring review, no claims/reservations; ten scopes ordered by smallest total symbol bytes',
              'originals':history,'registry':str(registry_path),'dedup_generation':pointer['generation'],
              'native_generation':native_pointer['sha256'],'databases_copied':0})
        return manifest
    finally:
        registry.close(); work.close(); native.close()


def summarize(prepared):
    operations = []
    for path in prepared.glob('selector-*/batch-run-results-*.json'):
        value = json.loads(path.read_text())
        operations.append({'path':str(path.relative_to(ROOT)), 'action':value['action'],
            'packets':len(value['receipts']), 'common_entry_seconds':value.get('common_entry_seconds'),
            'common_exit_seconds':value.get('common_exit_seconds'), 'full_generation_checks':value.get('full_generation_checks'),
            'packet_seconds_sum':sum(r['seconds'] for r in value['receipts']),
            'graph_seconds':value.get('graph_seconds'), 'graph_queries':value.get('graph_queries')})
    commands = []
    for path in prepared.glob('*.json'):
        if not path.name.startswith(('select-', 'finalize-', 'slice-', 'validation-', 'environment-')):
            continue
        value = json.loads(path.read_text())
        if 'argv' in value and 'seconds' in value:
            commands.append({'receipt':str(path.relative_to(ROOT)), 'seconds':value['seconds'],
                             'returncode':value['returncode']})
    completed = sorted(prepared.glob('attempt-*/COMPLETED.json'))
    return {'selector_operations':operations,'command_timings':commands,
            'attempts':[json.loads(p.read_text()) for p in completed]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--select-audit',action='store_true')
    choice.add_argument('--tasks')
    parser.add_argument('--groups',type=int,default=10)
    parser.add_argument('--per-group',type=int,default=10)
    parser.add_argument('--selection-only',action='store_true')
    parser.add_argument('--reuse-snapshot')
    parser.add_argument('--jobs',default='auto')
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--copy-budget-mib',type=int,default=DEFAULT_SNAPSHOT_COPY_BYTES//1024**2)
    parser.add_argument('--wait-for-context-lock',action='store_true',
                        help='Wait for an existing writer without polling; report dependency wait separately')
    args = parser.parse_args()
    output = inside(ROOT,args.out)
    if not output.is_relative_to(ROOT/'temp/recovery-work'):
        raise ContextError('Measurement output must be project recovery work')
    output.mkdir(parents=True,exist_ok=args.resume)
    prepared = output/'prepared'
    wait_started = time.perf_counter()
    if args.wait_for_context_lock:
        with (ROOT/'dependency-graph/state/context.lock').open('r') as lock:
            fcntl.flock(lock,fcntl.LOCK_SH)
            fcntl.flock(lock,fcntl.LOCK_UN)
    dependency_wait = time.perf_counter()-wait_started
    write(output/('DEPENDENCY_WAIT-'+str(time.time_ns())+'.json' if args.resume else 'DEPENDENCY_WAIT.json'),{'seconds':dependency_wait,'mechanism':'blocking shared lock; no polling; coordinator rechecks freshness'})
    started = time.perf_counter()
    begin = datetime.datetime.now(datetime.timezone.utc).isoformat()
    manifest = ((output/'TASKS.json' if args.resume else select_audit(output,prepared,args.groups,args.per_group))
                if args.select_audit else inside(ROOT,args.tasks))
    if args.selection_only:
        print(manifest.relative_to(ROOT)); return
    spec = importlib.util.spec_from_file_location('preparation_operator',ROOT/'uc-library/tools/recovery/select_context.py')
    operator = importlib.util.module_from_spec(spec);spec.loader.exec_module(operator)
    from context_batch import run
    result = {'started_utc':begin,'manifest':str(manifest.relative_to(ROOT)), 'manifest_sha256':sha(manifest),
              'workers_launched':0,'database_copies':0,'snapshot_copy_budget_bytes':args.copy_budget_mib*1024**2,'dependency_wait_seconds':dependency_wait,'mode':'audit' if args.select_audit else 'supplied task modes'}
    try:
        build_start = time.perf_counter()
        dispatch = run(operator,str(manifest.relative_to(ROOT)),str(prepared.relative_to(ROOT)),
                       jobs=args.jobs,reuse_snapshot=args.reuse_snapshot,resume=args.resume,
                       copy_budget_bytes=args.copy_budget_mib*1024*1024)
        result.update(success=True,preparation_seconds=time.perf_counter()-build_start,dispatch=str(dispatch))
    except Exception as error:
        result.update(success=False,error=str(error))
        raise
    finally:
        result.update(total_seconds=time.perf_counter()-started, finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      **summarize(prepared))
        write(output/('MEASUREMENT-retry-'+str(time.time_ns())+'.json' if args.resume else 'MEASUREMENT.json'),result)
        print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':
    main()
