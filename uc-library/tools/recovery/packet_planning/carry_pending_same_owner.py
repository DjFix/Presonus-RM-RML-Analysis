"""Relocate active same-owner claims into fresh packets after an authenticated old publication."""
import argparse
from contextlib import closing
import fcntl
from pathlib import Path
from packet_cycle import ROOT, CYCLE, read, rel, save
from context_batch import validate_tasks
from context_publication import authorization
from context_runtime import sha
from dedup_index import connect, dump, now
from dedup_work import active_index, validate_claim
from reconstruction_contract import validate_request

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--old',type=Path,nargs='+',default=[])
parser.add_argument('--pending-scope',type=Path,nargs='+',default=[])
parser.add_argument('--pending-original-manifest',type=Path,required=True)
parser.add_argument('--manifest',type=Path,required=True)
parser.add_argument('--batch',type=Path,required=True)
parser.add_argument('--owner-observation',type=Path,required=True)
parser.add_argument('--out',type=Path,required=True)
parser.add_argument('--apply-plan',type=Path)
a=parser.parse_args()
for path in [*a.old,*a.pending_scope,a.pending_original_manifest,a.manifest,a.batch,a.owner_observation,a.out]:
    if not path.resolve().is_relative_to(CYCLE):
        raise ValueError('Cycle-local inputs and outputs required')
if a.batch.exists() or a.out.exists():
    raise ValueError('Fresh batch and evidence outputs required')
observation=read(a.owner_observation)
allowed=set(observation['confirmed_unlaunched_and_unbound'])
manifest=read(a.manifest)
tasks=[read(ROOT/path) for path in manifest['tasks']]
validate_tasks(tasks,manifest['groups'])
new_packets={Path(packet).name:(packet,group['task_name'])
             for group in manifest['groups'] for packet in group['packets']}
if set(new_packets)!={t['task_id'] for t in tasks}:
    raise ValueError('Exact packet/task coverage required')
old={}
for old_path in a.old:
    prior=read(old_path)
    if prior['publication_state']!='complete':
        raise ValueError('Expected authenticated earlier complete publication')
    for worker in prior['workers']:
        owner=worker['arguments']['task_name']
        if owner not in allowed:
            continue
        for directory in worker['packets']:
            path=ROOT/directory
            authorization(ROOT,path)
            if path.name in old:
                raise ValueError('Multiple historical publications for same task')
            old[path.name]=(path,owner,old_path,'sealed_dispatch')

original_manifest=read(a.pending_original_manifest)
historical_owners={p: group['task_name'] for group in original_manifest['groups'] for p in group['packets']}
for scope_path in a.pending_scope:
    scope_plan=read(scope_path)
    outcome=read(scope_path.parent/'OUTCOME.json')
    if outcome['returncode']!=0 or not scope_plan['omitted']:
        raise ValueError('Expected completed compatible scoped publication and deferred originals')
    completed=read(ROOT/outcome['dispatch'])
    if completed['publication_state']!='complete':
        raise ValueError('Prior independent scope was not normally published')
    completed_packets={p for worker in completed['workers'] for p in worker['packets']}
    for path in scope_plan['omitted']:
        target=ROOT/path
        owner=historical_owners.get(path)
        if not owner:
            raise ValueError('No exact logical owner in the authenticated prior manifest: '+path)
        if owner not in allowed:
            continue
        if target.name in old or path in completed_packets or (target/'DISPATCH.json').exists():
            raise ValueError('Unexpected prior scope publication for deferred target')
        protected=scope_plan['protected_deferred'][path]
        if protected!={f.name:sha(f) for f in target.iterdir() if f.is_file()}:
            raise ValueError('Deferred frozen packet changed')
        batch=target.parent.parent
        if (sha(batch/'FROZEN.json')!=scope_plan['original_freeze_sha256'] or
                read(batch/'FROZEN.json')['manifest_sha256']!=sha(a.pending_original_manifest)):
            raise ValueError('Earlier batch freeze changed')
        member=read(target/'BATCH_MEMBER.json')
        if member!={'manifest':rel(batch/'BATCH_DISPATCH.json'),'state':'pending','version':1}:
            raise ValueError('Deferred target is no longer pending')
        old[target.name]=(target,owner,scope_path,'frozen_deferred')

with (ROOT/'dependency-graph/state/context.lock').open('rb') as graph:
    fcntl.flock(graph,fcntl.LOCK_SH if a.apply_plan is None else fcntl.LOCK_EX)
    active=read(ROOT/'dependency-graph/ACTIVE.json')
    if active['state_sha256']!=observation['current_generation']:
        raise ValueError('Required verified current graph differs')
    applied_packets=set()
    for intent in (CYCLE/'workspaces').glob('**/APPLY_INTENT.json'):
        plan=intent.parent/'PLAN.json'
        if not plan.is_file() or sha(plan)!=read(intent)['plan_sha256']:
            raise ValueError('Cannot verify earlier workspace apply intent: '+str(intent))
        for assignment in read(plan)['assignments']:
            applied_packets.update(str((ROOT/path).resolve()) for path in assignment['packets'])
    prepared=[]
    bind=[]
    for task in tasks:
        validate_request(ROOT,task)
        task_id=task['task_id']
        if task_id not in old:
            continue
        path,owner,seal,evidence_kind=old[task_id]
        if str(path.resolve()) in applied_packets:
            raise ValueError(f"Earlier packet is already physically bound: {task_id}")
        destination,group=new_packets[task_id]
        if owner!=group or destination!=rel(a.batch/'packets'/task_id):
            raise ValueError('Worker owner or only authorized packet location differs')
        req=read(path/'request.json')
        if set(req['owned_files'])!=set(task['owned_files']):
            raise ValueError(f'Owned file set differs at {task_id}')
        for key in ('task_id','targets','existing_work_item_id','namespace','mode','work_kind'):
            if req[key]!=task[key]:
                raise ValueError(f'Original identity or ownership differs at {task_id}: {key}')
        if not task.get('uncertainty_work'):
            raise ValueError('Selected source-body uncertainty needs reviewed new explicit binding')
        binding=req['work_binding']
        if binding['claim_owner']!=task_id or binding['work_item_id']!=task['existing_work_item_id']:
            raise ValueError('Expected identical claim owner and work item')
        prepared.append(dict(owner=owner,task_id=task_id,claim_id=binding['claim_id'],
                             work_item_id=binding['work_item_id'],targets=req['targets'],
                             prior_evidence=rel(seal),prior_evidence_sha256=sha(seal),prior_evidence_kind=evidence_kind,
                             prior_packet=rel(path),prior_request_sha256=sha(path/'request.json'),
                             new_packet=destination))
        bind.append(binding)
    if not prepared:
        raise ValueError('No existing exact claims to carry forward')
    data=dict(active_generation=active,claims=prepared,
              manifest=rel(a.manifest),manifest_sha256=sha(a.manifest),
              owner_observation=rel(a.owner_observation),owner_observation_sha256=sha(a.owner_observation),
              applied=False)
    prior_c,pointer=active_index(ROOT)
    prior_c.close()
    with closing(connect(ROOT/pointer['database'],readonly=a.apply_plan is None)) as c:
        c.execute('BEGIN' if a.apply_plan is None else 'BEGIN IMMEDIATE')
        try:
            for entry,binding in zip(prepared,bind,strict=True):
                validate_claim(c,binding,entry['prior_packet'])
            if a.apply_plan is None:
                c.rollback()
            else:
                if read(a.apply_plan)!=data:
                    raise ValueError('Fresh carried claim plan differs from reviewed dry run')
                for entry in prepared:
                    if c.execute("SELECT 1 FROM work_claims WHERE packet_path=? AND state='active'",
                                 (entry['new_packet'],)).fetchone():
                        raise ValueError('New packet path has an active binding')
                    cursor=c.execute("UPDATE work_claims SET packet_path=? WHERE id=? AND owner=? AND packet_path=? AND state='active'",
                                     (entry['new_packet'],entry['claim_id'],entry['task_id'],entry['prior_packet']))
                    if cursor.rowcount!=1:
                        raise ValueError('Concurrent claim or ownership change')
                    c.execute("INSERT INTO claim_history(claim_id,state,reason,observations,created_at) VALUES(?,?,?,?,?)",
                              (entry['claim_id'],'active','same-owner carry-forward from exact unlaunched packet after canonical source change',
                               dump(dict(entry,new_manifest_sha256=data['manifest_sha256'],dry_run_sha256=sha(a.apply_plan))),now()))
                c.commit()
                data['applied']=True
        except BaseException:
            c.rollback()
            raise
    save(a.out,data)
print(len(prepared),"same-owner claims validated; applied",data['applied'])
