"""Finish and publish an exact compatible subset from an interrupted maintained batch."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import fcntl, importlib.util, os, subprocess, sys, time
from pathlib import Path
from packet_cycle import ROOT,CYCLE,read,rel,save
from context_batch import Environment,check_inputs,check_registry_records
from context_resources import choose_limits
from context_runtime import sha
from context_work_batch import BatchWorkValidator
from early_conflicts import SelectedReadGuard
from group_dispatch import check_groups

parser=argparse.ArgumentParser(description=__doc__)
for name in ('batch','tasks','out','dispatch'):
    parser.add_argument('--'+name, required=True, type=Path)
parser.add_argument('--defer',nargs='+',required=True)
parser.add_argument('--production-continuation', help='Explicit maintained production reason across exact original members')
a=parser.parse_args()
batch=a.batch.resolve();out=a.out.resolve();dispatch=a.dispatch.resolve()
if not all(p.is_relative_to(CYCLE) for p in (batch,out,dispatch)) or out.exists() or dispatch.exists():
    raise ValueError('Use fresh cycle-local scope and dispatch paths')
spec=importlib.util.spec_from_file_location('select_context_operator',ROOT/'uc-library/tools/recovery/select_context.py')
operator=importlib.util.module_from_spec(spec);spec.loader.exec_module(operator)
started=time.monotonic()
with (batch/'coordinator.lock').open('rb') as owner_lock:
    fcntl.flock(owner_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    frozen_path=batch/'FROZEN.json';frozen=read(frozen_path)
    if frozen['manifest_sha256']!=sha(a.tasks) or (batch/'BATCH_DISPATCH.json').exists():
        raise ValueError('Unexpected original coordinator manifest/state')
    failures=list(batch.glob('attempt-*/FAILED.json'))
    if not failures or not any('Early selected-read conflict' in read(path)['error'] for path in failures):
        raise ValueError('Expected a real retained selected-read conflict')
    original=read(a.tasks)['groups']
    original_paths={p for g in original for p in g['packets']}
    deferred={p for p in original_paths if Path(p).name in a.defer}
    if len(deferred)!=len(set(a.defer)) or len(deferred)==len(original_paths):
        raise ValueError('Exact nonempty compatible and deferred scope required')
    groups=[]
    for g in original:
        keep=[p for p in g['execution_order'] if p not in deferred]
        if keep:
            groups.append(dict(g,packets=keep,execution_order=keep))
    paths=[p for g in groups for p in g['execution_order']]
    by_request={p:read(ROOT/p/'request.json') for p in paths}
    entries={p:read(ROOT/p/'context.json') for p in paths}
    pending={p:sha(ROOT/p/'BATCH_MEMBER.json') for p in paths}
    old_expected={'manifest':rel(batch/'BATCH_DISPATCH.json'),'state':'pending','version':1}
    for p,q in by_request.items():
        if read(ROOT/p/'BATCH_MEMBER.json')!=old_expected or (ROOT/p/'DISPATCH.json').exists():
            raise ValueError('Unexpected prior individual dispatch/membership: '+p)
        if entries[p]['task_sha256']!=sha(ROOT/p/'request.json') or entries[p]['state'] not in ('selected','dispatch_ready'):
            raise ValueError('Captured context or request changed: '+p)
    for g in groups:
        members=[by_request[p] for p in g['packets']]
        needs={x for r in members for x in r.get('included_dependency_work',[])}
        if not needs <= {r['work_binding']['work_item_id'] for r in members}:
            raise ValueError('Deferred packet is required within '+g['task_name'])
    branch=SelectedReadGuard(by_request, frozen['inputs']['active']['state_sha256'],
        {p:sha(ROOT/p/'request.json') for p in paths}, groups)
    for p in paths:
        branch.check(p,entries[p],by_request[p])
    initial_hashes={p:sha(ROOT/p/'context.json') for p in paths}
    protected={p:{x.name:sha(x) for x in (ROOT/p).iterdir() if x.is_file()} for p in sorted(deferred)}
    save(out/'PLAN.json',dict(groups=groups,omitted=sorted(deferred),original_freeze_sha256=sha(frozen_path),
                               original_snapshot_sha256=sha(batch/'SNAPSHOT.json'),initial_context_sha256=initial_hashes,
                               protected_deferred=protected,previous_pending_marker_sha256=pending,
                               selection_replay=False,claims_changed=False))
    scope=out/'GROUPS.json'
    manifest = dict(groups=groups, smaller_batch_authorization=
        'Root authorized independent reviewed rolling subsets after actual fresh selected overlap; deferred originals and claim bindings remain preserved.')
    if a.production_continuation:
        manifest['production_continuation'] = a.production_continuation
    save(scope,manifest)
    unfinished=[p for p in paths if entries[p]['state']=='selected']
    if unfinished:
        env=Environment(ROOT,batch)
        try:
            env.check_previous();env.pin_images()
            if env.images!=read(batch/'SNAPSHOT.json')['images']:
                raise ValueError('Frozen images disagree')
            env.start()
            with (ROOT/'dependency-graph/state/context.lock').open('rb') as lock:
                fcntl.flock(lock,fcntl.LOCK_SH)
                check_inputs(ROOT,operator,frozen['inputs'])
                check_registry_records(operator,list(by_request.values()),'Scoped original bindings changed')
                validator=BatchWorkValidator(ROOT)
                try:
                    for p in paths:
                        validator.validate(entries[p],p)
                    validator.finish()
                finally:
                    validator.close()
                limits=choose_limits('auto',len(unfinished))
                save(out/'RESOURCES.json',limits)
                def slice_packet(p):
                    if not (ROOT/p/'source-slices.json').exists():
                        env.slice(p,'cycle20-compatible-slice-'+Path(p).name+'-'+str(time.time_ns()))
                with ThreadPoolExecutor(max_workers=limits['limits']['slicing']) as pool:
                    list(pool.map(slice_packet,unfinished))
                errors=env.selector('finalize',unfinished,'cycle20-compatible-finalize-'+str(time.time_ns()))
                if errors:
                    raise ValueError(f'Scoped exact finalization failures: {errors}')
                check_inputs(ROOT,operator,frozen['inputs'])
                check_registry_records(operator,list(by_request.values()),'Scoped original bindings changed after finalization')
        finally:
            env.close()
    with (ROOT/'dependency-graph/state/context.lock').open('rb') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        check_inputs(ROOT,operator,frozen['inputs'])
        contexts={p:read(ROOT/p/'context.json') for p in paths}
        check_groups(groups,contexts,by_request,packets_per_worker=20,allow_smaller=True,
                     production_continuation=a.production_continuation)
        for p,hashes in protected.items():
            if {x.name:sha(x) for x in (ROOT/p).iterdir() if x.is_file()}!=hashes:
                raise ValueError('Deferred scope was modified: '+p)
        save(out/'FINALIZED.json',dict(context_sha256={p:sha(ROOT/p/'context.json') for p in paths},selection_replay=False))
        for p,digest in pending.items():
            source=ROOT/p/'BATCH_MEMBER.json'
            if sha(source)!=digest:
                raise ValueError('Prior member marker changed: '+p)
            target=out/'pending-members'/Path(p).name/'BATCH_MEMBER.json'
            target.parent.mkdir(parents=True,exist_ok=False)
            os.replace(source,target)
            if sha(target)!=digest:
                raise ValueError('Prior pending marker was not preserved: '+p)
    argv=[sys.executable,'dependency-graph/group_dispatch.py','--groups',rel(scope),'--out',rel(dispatch),
          '--packets-per-worker','20','--allow-smaller']
    save(out/'PUBLISH_ARGV.json',dict(argv=argv))
    result=subprocess.run(argv,cwd=ROOT,check=False)
    save(out/'OUTCOME.json',dict(returncode=result.returncode,dispatch=rel(dispatch/'BATCH_DISPATCH.json'),
                                 seconds=time.monotonic()-started,packets=len(paths),claims_changed=False,
                                 selection_replay=False))
    raise SystemExit(result.returncode)
