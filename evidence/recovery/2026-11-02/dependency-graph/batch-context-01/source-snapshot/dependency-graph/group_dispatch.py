"""Sealed multi-packet worker dispatch; all original packet gates remain mandatory."""
import argparse
import contextlib
import fcntl
import importlib.util
import json
import pathlib
import re
import shlex
import subprocess
import sys
import time

from context_runtime import ContextError, guard, inside, sha

ROOT = pathlib.Path(__file__).resolve().parents[1]


def check_groups(groups, entries, requests, packets_per_worker=5):
    if packets_per_worker not in (5, 10):
        raise ContextError("Supported packet counts per worker: five or ten")
    expected = 10 * packets_per_worker
    if len(groups) != 10:
        raise ContextError('Exactly ten worker groups required')
    names = [g['task_name'] for g in groups]
    if len(set(names)) != 10 or any(not re.fullmatch('[a-z][a-z0-9_]{0,63}', n) for n in names):
        raise ContextError('Unique valid worker names required')
    paths = [p for g in groups for p in g['packets']]
    if any(len(g['packets']) != packets_per_worker for g in groups) or len(set(paths)) != expected:
        raise ContextError('Exactly the configured distinct work packets per worker required')
    if len({e['task_id'] for e in entries.values()}) != expected:
        raise ContextError('Duplicate packet task identity')
    if len({e['generation_sha256'] for e in entries.values()}) != 1:
        raise ContextError('Mixed graph generations')
    works = [e['work_binding']['work_item_id'] for e in entries.values()]
    if len(set(works)) != expected:
        raise ContextError('Duplicate unique work')
    identities = []
    for p in paths:
        e = entries[p]
        if e.get('state') != 'dispatch_ready':
            raise ContextError('Empty/unfinalized packet')
        targets = e['work_binding']['covered_occurrences']
        if len(targets) != 1:
            raise ContextError('Trial requires one original symbol per packet; packet expands coverage')
        identities.extend((t['elf_sha256'], t['original_mangled']) for t in targets)
    if len(set(identities)) != expected:
        raise ContextError('Duplicate original identity')
    for g in groups:
        if not g.get('scope_reason') or set(g.get('execution_order', [])) != set(g['packets']) or len(g['execution_order']) != packets_per_worker:
            raise ContextError('Scope reason and exact intra-worker execution order required')
        owned = set().union(*(set(requests[p]['owned_files']) for p in g['packets']))
        for h in groups:
            if h is g:
                continue
            other = set().union(*(set(entries[p]['selected_file_sha256']) | set(requests[p]['owned_files']) for p in h['packets']))
            if owned & other:
                raise ContextError('Inter-worker write/read overlap: ' + json.dumps(sorted(owned & other)))
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--groups', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--packets-per-worker', type=int, choices=(5, 10), default=5)
    a = parser.parse_args()
    groups_path = inside(ROOT, a.groups)
    group_bytes = groups_path.read_bytes()
    import hashlib
    groups_digest = hashlib.sha256(group_bytes).hexdigest()
    groups = json.loads(group_bytes)['groups']
    output = inside(ROOT, a.out)
    if not output.is_relative_to(ROOT / 'temp/recovery-work'):
        raise ContextError('Output must be in project recovery work')
    output.mkdir(parents=True, exist_ok=False)
    spec = importlib.util.spec_from_file_location('select_context_operator', ROOT/'uc-library/tools/recovery/select_context.py')
    operator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(operator)
    with (ROOT/'dependency-graph/state/context.lock').open('a') as lock, contextlib.ExitStack() as cleanup:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if sha(groups_path) != groups_digest:
            raise ContextError('Group assignments changed while acquiring lock')
        active = json.loads((ROOT/'dependency-graph/ACTIVE.json').read_text())
        guard(ROOT, active)
        paths = [p for g in groups for p in g['packets']]
        entries = {p: json.loads((inside(ROOT,p)/'context.json').read_text()) for p in paths}
        requests = {p: json.loads((inside(ROOT,p)/'request.json').read_text()) for p in paths}
        expected_manifests = {p:sha(inside(ROOT,p)/'context.json') for p in paths}
        check_groups(groups, entries, requests, a.packets_per_worker)
        from context_work_batch import BatchWorkValidator
        work_validator = BatchWorkValidator(ROOT)
        cleanup.callback(work_validator.close)
        for path in paths:
            work_validator.validate(entries[path],path)
        # Validate every selected record and full packet in the existing operator,
        # while holding the shared publication lock across all packet checks.
        for p in paths:
            if (inside(ROOT,p)/'DISPATCH.json').exists():
                raise ContextError('Already dispatched packet: '+p)
            if (inside(ROOT,p)/'BATCH_MEMBER.json').exists():
                raise ContextError('Packet already belongs to a batch; resume its coordinator: '+p)
        from context_publication import atomic_json
        for p in paths:
            atomic_json(inside(ROOT,p)/'BATCH_MEMBER.json', {'version':1,'state':'pending',
                        'manifest':str((output/'BATCH_DISPATCH.json').relative_to(ROOT))})
        for p in paths:
            if operator.enrich(requests[p])['originals'] != requests[p]['originals']:
                raise ContextError('Selected original/evidence binding changed: '+p)
        specification = output/'validation-packets.json'
        specification.write_text(json.dumps(paths,indent=2)+'\n')
        command = operator.selector_command(ROOT,output,'batch-validate')
        command += ['--packets-json',str(specification.relative_to(ROOT))]
        started = time.time()
        result = subprocess.run(['sg','docker','-c',shlex.join(command)],cwd=ROOT,capture_output=True,text=True)
        (output/'batch-validate.log').write_text(result.stdout+result.stderr)
        (output/'validation-receipts.json').write_text(json.dumps({'argv':command,'seconds':time.time()-started,'returncode':result.returncode},indent=2)+'\n')
        if result.returncode:
            raise ContextError('Batch validation failed; no workers authorized')
        # Existing packet validation also authenticates each SUBAGENT_PROMPT.
        # Materialize per-packet baseline dispatch only after every gate passes.
        guard(ROOT,active)
        workers = []
        for g in groups:
            messages=[]
            for p in g['execution_order']:
                packet=inside(ROOT,p)
                single={'task_name':requests[p]['task_id'],'fork_turns':'none','message':(packet/'SUBAGENT_PROMPT.md').read_text()+' Context manifest SHA-256: '+sha(packet/'context.json')}
                messages.append(single['message'])
            owned=sorted(set().union(*(set(requests[p]['owned_files']) for p in g['packets'])))
            message=(f'You are one reconstruction worker owning {a.packets_per_worker} sealed work packets as a single coherent scope. Read every packet before editing. '+
                     'Scope rationale: '+g['scope_reason']+'\nExecution order: '+json.dumps(g['execution_order'])+
                     '\nOwned file union: '+json.dumps(owned)+
                     '\nDeliver one HANDOFF v1 per packet with its exact task_id and originals, then an aggregate index. '+
                     'Shared owned files may implement multiple methods; seal their hashes after every owned method is finished. '+
                     'Do not spawn agents. Record provider session ID, UTC phase timestamps, tool durations and context/dependency observations for each symbol. '+
                     'Use uc-library/.venv/bin tools. Sandbox bwrap currently fails: use require_escalated for shell tools. '+
                     'No shared build/ledger edits. Ask Root for missing context with packet/seed/query/reason; no broad dependency scans.\n\n'+
                     'Read SUBAGENT_PROMPT.md, TASK.md, ELF_CONTEXT.md, SOURCE_SLICES.md and CONTEXT.md in every packet listed above. The authenticated packet prompts apply in full. Manifest bindings: '+json.dumps({p:sha(inside(ROOT,p)/'context.json') for p in g['packets']}))
            workers.append({'packets':g['packets'],'arguments':{'task_name':g['task_name'],'fork_turns':'none','message':message}})
        payload={'version':1,'packets_per_worker':a.packets_per_worker,'generation':active['state_sha256'],'groups_sha256':groups_digest,
                 'operator_sha256':sha(pathlib.Path(__file__)), 'workers':workers,'mode':'sealed_before_first_worker_write',
                 'packet_manifests':{p:sha(inside(ROOT,p)/'context.json') for p in paths},'dependency_conflicts':[]}
        # Fresh selected registry bindings are required again at the publication barrier.
        for p in paths:
            if operator.enrich(requests[p])['originals'] != requests[p]['originals']:
                raise ContextError('Selected original/evidence binding changed before publication: '+p)
        from context_publication import publish_batch, verify_packet_files
        if json.loads((ROOT/'dependency-graph/ACTIVE.json').read_text()) != active:
            raise ContextError('Generation changed before publication')
        guard(ROOT,active)
        verify_packet_files(ROOT,paths,expected_manifests)
        work_validator.finish()
        if sha(groups_path) != groups_digest:
            raise ContextError('Group assignments changed before publication')
        print(publish_batch(ROOT,output,payload,paths))


if __name__=='__main__':
    try:main()
    except (ContextError,ValueError,KeyError) as e:raise SystemExit('GROUP DISPATCH BLOCKED: '+str(e))
