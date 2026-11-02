"""Memgraph context gate before collaboration.spawn_agent; registry stays read-only."""
import argparse
import fcntl
import hashlib
import json
import pathlib
import re
import shlex
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'dependency-graph'))
sys.path.insert(0, str(ROOT / 'uc-library/tools/registry'))
from context_runtime import ContextError, guard, inside, sha, validate_task, validate_original_scope
from refresh_graph import ensure_fresh
from memgraph_endpoint import memgraph_uri
import adapter


def enrich(task):
    validate_task(task)
    enriched = dict(task)
    identities = []
    with adapter.snapshot(ROOT / 'uc-library') as snapshot:
        for target in task['targets']:
            elf, mangled = target['original_elf_sha256'], target['mangled']
            row = snapshot.c.execute('SELECT * FROM records WHERE elf=? AND mangled=?', (elf,mangled)).fetchone()
            record = json.loads(row['metadata']) if row else None
            rows = [dict(r) for r in snapshot.c.execute(
                'SELECT * FROM catalog_symbols WHERE elf=? AND mangled=?', (elf,mangled))]
            if target.get('anchor'):
                rows = [r for r in rows if r['anchor'] == target['anchor']]
            elif record:
                address = record.get('original_address', record.get('address'))
                size = record.get('original_size', record.get('size'))
                rows = [r for r in rows if r['address'] == address and r['size'] == size]
            elif 'address' in target and 'size' in target:
                rows = [r for r in rows if r['address'] == target['address'] and r['size'] == target['size']]
            if len(rows) != 1:
                raise ContextError('Resolve exact catalog anchor/range; ambiguous or absent original: ' + mangled)
            original = rows[0]
            validate_original_scope(task, original)
            identities.append({'original': original, 'record': record})
        enriched['originals'] = identities
        enriched['registry_guard'] = snapshot.guard
    for path in task.get('owned_files', []):
        inside(ROOT, path)
    return enriched


def selector_command(root, out, action):
    # Reused observations have absolute, repository-contained symlinks. Preserve
    # the host root inside the container rather than changing it to /workspace.
    argv = ['docker','run','--name','recovery-context-'+str(time.time_ns()),
            '--network','dependency-graph-experiment','--memory=2g','--cpus=2',
            '--workdir',str(root),'-e','DEPENDENCY_GRAPH_ROOT='+str(root),
            '-e','TMPDIR='+str(out),'-e','SQLITE_TMPDIR='+str(out),
            '-v',str(root)+':'+str(root)+':ro','-v',str(out)+':'+str(out)+':rw',
            '--user','1000:1000','dependency-graph-runner:01',
            str(root/'dependency-graph/context_selector.py'),action,'--out',str(out.relative_to(root))]
    if action=='register':
        argv[argv.index('--user'):argv.index('--user')] = [
            '-v',str(root/'dependency-graph')+':'+str(root/'dependency-graph')+':rw']
    return argv


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('register', 'prepare', 'validate', 'dispatch', 'expand', 'batch-dispatch', 'batch-prepare'))
    p.add_argument('--tasks')
    p.add_argument('--jobs', default='auto')
    p.add_argument('--selection-jobs', type=int)
    p.add_argument('--slicing-jobs', type=int)
    p.add_argument('--resume', action='store_true')
    p.add_argument('--memgraph-cap', type=int, default=4)
    p.add_argument('--selection-memory-mib', type=int, default=512)
    p.add_argument('--slicing-memory-mib', type=int, default=1536)
    p.add_argument('--reserve-memory-mib', type=int, default=1024)
    p.add_argument('--task')
    p.add_argument('--out')
    p.add_argument('--packet')
    p.add_argument('--query', choices=('callers', 'callees', 'references', 'overrides', 'source_files', 'proofs','native_body','native_data'))
    p.add_argument('--seed')
    p.add_argument('--reason')
    p.add_argument('--baseline',action='store_true')
    p.add_argument('--packets',nargs='+')
    a = p.parse_args()
    if a.action == 'batch-prepare':
        if not a.tasks or not a.out:
            p.error('--tasks and --out required')
        memgraph_uri(ROOT)
        import context_batch
        print(context_batch.run(sys.modules[__name__], a.tasks, a.out, a.jobs,
                                a.selection_jobs, a.slicing_jobs, a.resume,
                                resource_options={'memgraph_cap': a.memgraph_cap,
                                    'selection_memory_mib': a.selection_memory_mib,
                                    'slicing_memory_mib': a.slicing_memory_mib,
                                    'reserve_memory_mib': a.reserve_memory_mib}))
        return
    memgraph_uri(ROOT)  # Block before obtaining claims while infrastructure moves.
    # Serialize publication with packet construction/dispatch. Batch invokes
    # individually locked dispatches and never starts workers before all pass.
    phase_timings = []
    operation_started = time.perf_counter()
    lock_started = time.perf_counter()
    lock_stream = None
    if a.action not in ('batch-dispatch', 'register'):
        # Registration CLI takes its own writer lock; avoid cross-process nested flock.
        lock_path = ROOT/'dependency-graph/state/context.lock'
        lock_path.parent.mkdir(parents=True,exist_ok=True)
        lock_stream = lock_path.open('a')
        fcntl.flock(lock_stream,fcntl.LOCK_EX)
        phase_timings.append({'phase': 'lock_wait', 'seconds': time.perf_counter()-lock_started})
    prepared_task = None
    if a.action == 'prepare':
        from dedup_work import claim_task
        claim_started = time.perf_counter()
        prepared_task = claim_task(ROOT, enrich(json.loads(inside(ROOT,a.task).read_text())), a.out)
        # All covered originals become actual packet targets; each needs a body.
        prepared_task = enrich(prepared_task)
        phase_timings.append({'phase': 'claim/enrich', 'seconds': time.perf_counter()-claim_started})
        refresh_started = time.perf_counter()
        ensure_fresh()
        phase_timings.append({'phase': 'refresh', 'seconds': time.perf_counter()-refresh_started})
    if a.action=='batch-dispatch':
        if not a.packets or not a.out:p.error('--packets and --out required')
        from context_publication import publish_batch, verify_packet_files
        import contextlib
        from context_work_batch import BatchWorkValidator
        from context_batch import check_conflicts
        packets=[inside(ROOT,path) for path in a.packets]
        paths=[str(packet.relative_to(ROOT)) for packet in packets]
        if len(set(paths)) != len(paths):raise ContextError('Duplicate packet paths')
        output=inside(ROOT,a.out)
        if not output.is_relative_to(ROOT/'temp/recovery-work'):raise ContextError('Batch output must be project recovery work')
        output.mkdir(parents=True,exist_ok=False)
        lock_path=ROOT/'dependency-graph/state/context.lock'
        with lock_path.open('a') as lock, contextlib.ExitStack() as cleanup:
            waiting=time.perf_counter()
            fcntl.flock(lock,fcntl.LOCK_EX)
            lock_wait=time.perf_counter()-waiting
            active=json.loads((ROOT/'dependency-graph/ACTIVE.json').read_text())
            guard(ROOT,active)
            entries=[json.loads((packet/'context.json').read_text()) for packet in packets]
            requests=[json.loads((packet/'request.json').read_text()) for packet in packets]
            seals={path:sha(packet/'context.json') for path,packet in zip(paths,packets)}
            check_conflicts(entries,requests)
            work_validator = BatchWorkValidator(ROOT)
            cleanup.callback(work_validator.close)
            for entry,path in zip(entries,paths):
                work_validator.validate(entry,path)
            for packet,request in zip(packets,requests):
                if (packet/'DISPATCH.json').exists():raise ContextError('Packet already dispatched')
                if enrich(request)['originals'] != request['originals']:raise ContextError('Selected registry binding changed')
                member=packet/'BATCH_MEMBER.json'
                if member.exists():raise ContextError('Packet already belongs to a batch; resume its coordinator')
            # Reserve all members before any validation; no standalone dispatch
            # may turn a partially complete batch into launch permission.
            from context_publication import atomic_json
            for packet in packets:
                atomic_json(packet/'BATCH_MEMBER.json',{'version':1,'state':'pending',
                    'manifest':str((output/'BATCH_DISPATCH.json').relative_to(ROOT))})
            specification=output/'validation-packets.json'
            specification.write_text(json.dumps(paths,indent=2)+'\n')
            command=selector_command(ROOT,output,'batch-validate')+['--packets-json',str(specification.relative_to(ROOT))]
            started=time.perf_counter()
            with (output/'batch-validate.log').open('x') as log:
                result=subprocess.run(['sg','docker','-c',shlex.join(command)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            (output/'validation-receipt.json').write_text(json.dumps({'argv':command,'returncode':result.returncode,
                'seconds':time.perf_counter()-started,'lock_wait_seconds':lock_wait},indent=2)+'\n')
            if result.returncode:raise ContextError('Batch validation failed; no workers authorized; claims retained')
            if json.loads((ROOT/'dependency-graph/ACTIVE.json').read_text()) != active:raise ContextError('Generation changed')
            guard(ROOT,active)
            for request in requests:
                if enrich(request)['originals'] != request['originals']:raise ContextError('Selected registry binding changed before publication')
            work_validator.finish()
            check_conflicts(entries,requests)
            verify_packet_files(ROOT,paths,seals)
            payload=[{'packet':path,'context_sha256':seals[path],
                      'arguments':{'task_name':request['task_id'],'fork_turns':'none',
                          'message':(packet/'SUBAGENT_PROMPT.md').read_text()+' Context manifest SHA-256: '+seals[path]}}
                     for path,packet,request in zip(paths,packets,requests)]
            print(publish_batch(ROOT,output,{'version':1,'generation':active['state_sha256'],
                'workers':payload,'mode':'sealed_before_first_worker_write','dependency_conflicts':[]},paths))
        return
    common_started = time.perf_counter()
    active_path = ROOT / 'dependency-graph/ACTIVE.json'
    if a.action != 'register':
        active = json.loads(active_path.read_text())
        if not (a.action=='expand' and a.baseline):guard(ROOT, active)
    if a.action in ('prepare', 'register', 'expand'):
        if not a.out:
            p.error('--out required; existing outputs are never overwritten')
        out = inside(ROOT, a.out)
        if not (out.is_relative_to(ROOT/'temp/recovery-work') or out.is_relative_to(ROOT/'evidence/recovery')):
            raise ContextError('Context output must be in project recovery work/evidence')
        out.mkdir(parents=True, exist_ok=False)
    else:
        if not a.packet:
            p.error('--packet required')
        out = inside(ROOT, a.packet)
        original_request=json.loads((out/'request.json').read_text())
        if enrich(original_request)['originals'] != original_request['originals']:
            raise ContextError('Selected original/evidence bindings changed; prepare a new packet')
    if a.action == 'prepare':
        task = prepared_task
        (out/'request.json').write_text(json.dumps(task, indent=2)+'\n')
    if a.action == 'expand':
        if not a.packet or not a.query or not a.seed or not a.reason:
            p.error('Expansion needs --packet --query --seed --reason')
        parent = inside(ROOT,a.packet)
        request = {'parent':str(parent.relative_to(ROOT)), 'query':a.query,
                   'seed':a.seed, 'reason':a.reason,'view':'task-baseline' if a.baseline else 'current'}
        (out/'expansion-request.json').write_text(json.dumps(request,indent=2)+'\n')
    phase_timings.append({'phase': 'common_checks', 'seconds': time.perf_counter()-common_started})
    argv = selector_command(ROOT, out, a.action)
    start = time.perf_counter()
    log_name = a.action+'-'+str(time.time_ns())
    with (out/(log_name+'.log')).open('w') as log:
        result = subprocess.run(['sg','docker','-c',shlex.join(argv)], stdout=log,stderr=subprocess.STDOUT)
    receipt = {'argv':argv,'returncode':result.returncode,'seconds':time.perf_counter()-start,
               'phase': 'environment_and_'+a.action, 'preceding_phases': phase_timings}
    (out/(log_name+'.json')).write_text(json.dumps(receipt,indent=2)+'\n')
    if result.returncode:
        print((out/(log_name+'.log')).read_text()[-5000:])
        raise SystemExit(result.returncode)
    print((out/(log_name+'.log')).read_text())
    if a.action=='prepare':
        relative=str(out.relative_to(ROOT))
        analysis=['docker','run','--name','recovery-context-slices-'+str(time.time_ns()),
                  '--network=none','--memory=3g','--cpus=2','-e','DEPENDENCY_GRAPH_ROOT='+str(ROOT),
                  '-v',str(ROOT)+':'+str(ROOT)+':ro','-v',str(out)+':'+str(out)+':rw',
                  '-v','/usr/include/openssl:/usr/include/openssl:ro',
                  '-v','/usr/include/x86_64-linux-gnu/openssl:/usr/include/x86_64-linux-gnu/openssl:ro',
                  '--user','1000:1000','dependency-graph-analysis:01',
                  str(ROOT/'dependency-graph/context_slices.py'),str(out)]
        slicing_started = time.perf_counter()
        with (out/'source-slices.log').open('w') as log:
            replay=subprocess.run(['sg','docker','-c',shlex.join(analysis)],stdout=log,stderr=subprocess.STDOUT)
        (out/'source-slices-command.json').write_text(json.dumps({'argv':analysis,'returncode':replay.returncode,'seconds':time.perf_counter()-slicing_started},indent=2)+'\n')
        if replay.returncode:raise ContextError('Source slicing failed; packet is not dispatchable: '+(out/'source-slices.log').read_text()[-2000:])
        finalize=list(argv);finalize[finalize.index('prepare')]='finalize';finalize[finalize.index('--name')+1]+='-finalize'
        finalize_started = time.perf_counter()
        with (out/'finalize.log').open('w') as log:
            final=subprocess.run(['sg','docker','-c',shlex.join(finalize)],stdout=log,stderr=subprocess.STDOUT)
        (out/'finalize-command.json').write_text(json.dumps({'argv':finalize,'returncode':final.returncode,'seconds':time.perf_counter()-finalize_started},indent=2)+'\n')
        if final.returncode:raise ContextError((out/'finalize.log').read_text()[-2000:])
        print((out/'finalize.log').read_text())
    (out/('operation-timings-'+str(time.time_ns())+'.json')).write_text(json.dumps({
        'action': a.action, 'wall_seconds': time.perf_counter()-operation_started,
        'phases': phase_timings, 'selector_seconds': receipt['seconds'],
        'legacy_environment_note': 'Legacy docker-run duration includes environment startup; batch environment startup is measured separately.'}, indent=2)+'\n')
    if a.action == 'dispatch':
        print((out/'DISPATCH.json').read_text())


if __name__ == '__main__':
    try:
        main()
    except (ContextError, ValueError, KeyError) as exc:
        raise SystemExit('CONTEXT BLOCKED: '+str(exc))
