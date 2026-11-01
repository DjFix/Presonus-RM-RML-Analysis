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
from context_runtime import ContextError, guard, inside, sha, validate_task
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
            if not re.search(r'(?<![A-Za-z0-9_])'+re.escape(task['namespace'].rstrip(':'))+r'::', original['demangled']):
                raise ContextError('Target outside assigned namespace: ' + original['demangled'])
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
    p.add_argument('action', choices=('register', 'prepare', 'validate', 'dispatch', 'expand', 'batch-dispatch'))
    p.add_argument('--task')
    p.add_argument('--out')
    p.add_argument('--packet')
    p.add_argument('--query', choices=('callers', 'callees', 'references', 'overrides', 'source_files', 'proofs','native_body','native_data'))
    p.add_argument('--seed')
    p.add_argument('--reason')
    p.add_argument('--baseline',action='store_true')
    p.add_argument('--packets',nargs='+')
    a = p.parse_args()
    memgraph_uri(ROOT)  # Block before obtaining claims while infrastructure moves.
    # Serialize publication with packet construction/dispatch. Batch invokes
    # individually locked dispatches and never starts workers before all pass.
    lock_stream = None
    if a.action != 'batch-dispatch':
        lock_path = ROOT/'dependency-graph/state/context.lock'
        lock_path.parent.mkdir(parents=True,exist_ok=True)
        lock_stream = lock_path.open('a')
        fcntl.flock(lock_stream,fcntl.LOCK_EX)
    prepared_task = None
    if a.action == 'prepare':
        from dedup_work import claim_task
        prepared_task = claim_task(ROOT, enrich(json.loads(inside(ROOT,a.task).read_text())), a.out)
        # All covered originals become actual packet targets; each needs a body.
        prepared_task = enrich(prepared_task)
        ensure_fresh()
    if a.action=='batch-dispatch':
        if not a.packets or not a.out:p.error('--packets and --out required')
        packets=[inside(ROOT,p) for p in a.packets]
        entries=[json.loads((p/'context.json').read_text()) for p in packets]
        requests=[json.loads((p/'request.json').read_text()) for p in packets]
        from dedup_work import validate_batch_work
        validate_batch_work(ROOT, entries, [str(p.relative_to(ROOT)) for p in packets])
        if len({e['task_id'] for e in entries})!=len(entries):raise ContextError('Duplicate subagent task names')
        if len({e['generation_sha256'] for e in entries})!=1:raise ContextError('Mixed graph generations')
        for i,request in enumerate(requests):
            owned=set(request.get('owned_files',[]))
            for j,other in enumerate(entries):
                if i==j:continue
                conflict=owned & (set(other['selected_file_sha256']) | set(requests[j].get('owned_files',[])))
                if conflict:raise ContextError('Not an independent batch; dependency order required: '+json.dumps(sorted(conflict)))
        output=inside(ROOT,a.out)
        if not output.is_relative_to(ROOT/'temp/recovery-work'):raise ContextError('Batch output must be project recovery work')
        output.mkdir(parents=True,exist_ok=False)
        payload=[]
        for packet in packets:
            command=[sys.executable,str(pathlib.Path(__file__).resolve()),'dispatch','--packet',str(packet.relative_to(ROOT))]
            result=subprocess.run(command,cwd=ROOT,text=True,capture_output=True)
            (output/(packet.name+'.log')).write_text(result.stdout+result.stderr)
            if result.returncode:raise ContextError('Batch dispatch failed; do not spawn any worker: '+result.stdout+result.stderr)
            payload.append({'packet':str(packet.relative_to(ROOT)),
                            'context_sha256':sha(packet/'context.json'),
                            'arguments':json.loads((packet/'DISPATCH.json').read_text())})
        (output/'BATCH_DISPATCH.json').write_text(json.dumps({'generation':entries[0]['generation_sha256'],
            'workers':payload,'mode':'sealed_before_first_worker_write','dependency_conflicts':[]},indent=2)+'\n')
        print(str(output/'BATCH_DISPATCH.json'));return
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
    argv = selector_command(ROOT, out, a.action)
    start = time.perf_counter()
    log_name = a.action+'-'+str(time.time_ns())
    with (out/(log_name+'.log')).open('w') as log:
        result = subprocess.run(['sg','docker','-c',shlex.join(argv)], stdout=log,stderr=subprocess.STDOUT)
    receipt = {'argv':argv,'returncode':result.returncode,'seconds':time.perf_counter()-start}
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
        with (out/'source-slices.log').open('w') as log:
            replay=subprocess.run(['sg','docker','-c',shlex.join(analysis)],stdout=log,stderr=subprocess.STDOUT)
        (out/'source-slices-command.json').write_text(json.dumps({'argv':analysis,'returncode':replay.returncode},indent=2)+'\n')
        if replay.returncode:raise ContextError('Source slicing failed; packet is not dispatchable: '+(out/'source-slices.log').read_text()[-2000:])
        finalize=list(argv);finalize[finalize.index('prepare')]='finalize';finalize[finalize.index('--name')+1]+='-finalize'
        with (out/'finalize.log').open('w') as log:
            final=subprocess.run(['sg','docker','-c',shlex.join(finalize)],stdout=log,stderr=subprocess.STDOUT)
        (out/'finalize-command.json').write_text(json.dumps({'argv':finalize,'returncode':final.returncode},indent=2)+'\n')
        if final.returncode:raise ContextError((out/'finalize.log').read_text()[-2000:])
        print((out/'finalize.log').read_text())
    if a.action == 'dispatch':
        print((out/'DISPATCH.json').read_text())


if __name__ == '__main__':
    try:
        main()
    except (ContextError, ValueError, KeyError) as exc:
        raise SystemExit('CONTEXT BLOCKED: '+str(exc))
