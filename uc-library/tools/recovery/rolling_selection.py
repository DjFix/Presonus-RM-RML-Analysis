#!/usr/bin/env python3
"""Read-only rolling queue preflight. Eligibility never replaces sealed contracts/packets.

Current catalog/readiness and every unique-work member are checked before native
boundary inspection. Blocked or reserved work is parked, never a whole-queue error.
"""
import argparse
from collections import Counter, defaultdict
import datetime
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys


def read_db(path):
    db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA query_only=ON')
    db.execute('BEGIN')
    return db


def eligibility(members, catalog, admitted, active, reserved, compiled):
    reasons = set()
    for m in members:
        identity = (m['elf_sha256'], m['original_mangled'])
        task = catalog.get(m['catalog_anchor'])
        if task is None:
            reasons.add('missing_current_catalog_identity')
        elif task['state'] in ('blocked', 'assigned', 'in_progress', 'done'):
            reasons.add('catalog_' + task['state'])
        elif task['notes']:
            reasons.add('history_requires_review')
        if identity in admitted:
            reasons.add('already_admitted')
        if m['id'] in reserved:
            reasons.add('carryover_owner')
        if m['id'] in active:
            reasons.add('active_owner')
        if m['original_mangled'] in compiled:
            reasons.add('canonical_compiled_symbol')
        if m['strategy'] != 'reconstruct':
            reasons.add('source_provider_or_other_strategy')
    return sorted(reasons)


# Explicit known compiler/C-runtime families; this is routing, never provider proof.
RUNTIME_NAMES = {
    '__cxa_end_cleanup', '__dynamic_cast', '__cxa_guard_acquire',
    '__cxa_guard_release', '__cxa_guard_abort', '__cxa_atexit', '__aeabi_atexit',
    'operator new(unsigned int)', 'operator new[](unsigned int)',
    'operator delete(void*)', 'operator delete[](void*)',
    'strlen', 'strcmp', 'strncmp', 'strcpy', 'strncpy', 'strcat', 'strncat',
    'strstr', 'strchr', 'strrchr', 'memset', 'memcpy', 'memmove', 'memcmp',
    'malloc', 'calloc', 'realloc', 'free', 'snprintf', 'vsnprintf',
    'floor', 'floorf', 'ceil', 'ceilf', 'sqrt', 'sqrtf', 'pow', 'powf',
    'log', 'logf', 'log10', 'log10f', 'exp', 'expf', 'sin', 'sinf', 'cos', 'cosf',
    '__fixsfsi', '__fixdfsi', '__fixunssfsi', '__fixunsdfsi',
    '__floatsisf', '__floatsidf', '__floatunsisf', '__floatunsidf',
    '__extendsfdf2', '__truncdfsf2', '__addsf3', '__subsf3', '__mulsf3', '__divsf3',
    '__adddf3', '__subdf3', '__muldf3', '__divdf3',
    '__aeabi_fcmpgt', '__aeabi_fcmplt', '__aeabi_fcmpeq', '__aeabi_fcmpge', '__aeabi_fcmple',
    '__aeabi_dcmpgt', '__aeabi_dcmplt', '__aeabi_dcmpeq', '__aeabi_dcmpge', '__aeabi_dcmple',
    '__aeabi_f2iz', '__aeabi_f2uiz', '__aeabi_d2iz', '__aeabi_d2uiz',
    '__aeabi_i2f', '__aeabi_ui2f', '__aeabi_i2d', '__aeabi_ui2d', '__aeabi_f2d', '__aeabi_d2f',
    '__aeabi_fadd', '__aeabi_fsub', '__aeabi_fmul', '__aeabi_fdiv',
    '__aeabi_dadd', '__aeabi_dsub', '__aeabi_dmul', '__aeabi_ddiv',
    '__aeabi_idiv', '__aeabi_idivmod', '__aeabi_uidiv', '__aeabi_uidivmod',
    '__aeabi_ldivmod', '__aeabi_uldivmod', '__divsi3', '__udivsi3', '__modsi3', '__umodsi3',
}


def classify_boundary(boundary):
    if boundary['kind'] == 'ARM_INDIRECT_REVIEW_CANDIDATE':
        return 'indirect_requires_explicit_review'
    if boundary['available_originals']:
        return 'current_source_binding_requires_contract_review'
    names = boundary['target_names']
    if names and all(n.split('@', 1)[0] in RUNTIME_NAMES for n in names):
        return 'runtime_provider_requires_binding'
    return 'missing_application_or_unknown_dependency'


def enrich_reserve(report):
    for candidate in report['candidates']:
        for boundary in candidate['direct_boundaries']:
            boundary['routing'] = classify_boundary(boundary)
        candidate['runtime_provider_boundaries'] = [b for b in candidate['direct_boundaries']
            if b['routing'] == 'runtime_provider_requires_binding']
        candidate['missing_application_boundaries'] = [b for b in candidate['direct_boundaries']
            if b['routing'] == 'missing_application_or_unknown_dependency']
        candidate['unreviewed_indirect_boundaries'] = [b for b in candidate['direct_boundaries']
            if b['routing'] == 'indirect_requires_explicit_review']
    report['runtime_routing_policy'] = 'Exact whitelist only; retains every original target and site. Runtime classification does not mark boundary available, establish firmware equivalence, or authorize dispatch; Root must bind real runtime/native-oracle evidence in bounded contract.'
    return report


def preflight(root, limit):
    manifest = json.loads((root/'uc-library/validation/registry-sqlite/ACTIVE.json').read_text())
    dedup_manifest = json.loads((root/'dependency-graph/DEDUP_ACTIVE.json').read_text())
    registry = read_db(root/manifest['database']['path'])
    dedup = read_db(root/dedup_manifest['database'])
    native_manifest = json.loads((root/'dependency-graph/NATIVE_ACTIVE.json').read_text())
    native_path = root/native_manifest['database']
    stat_before = native_path.stat()
    digest = hashlib.sha256()
    with native_path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
    if digest.hexdigest() != native_manifest['sha256']:raise ValueError('Native generation hash mismatch')
    native = read_db(native_path)
    sys.path.insert(0,str(root/'dependency-graph'))
    from execution_review import collect, _node_identities
    native_identities = _node_identities(native)
    catalog = {x['anchor']: dict(x) for x in registry.execute('SELECT s.*,t.state,t.notes,t.revision FROM catalog_symbols s JOIN catalog_tasks t USING(anchor)')}
    admitted = {(x['elf'],x['mangled']) for x in registry.execute('SELECT elf,mangled FROM records')}
    members = defaultdict(list)
    occurrences = {x['id']:dict(x) for x in dedup.execute('SELECT * FROM symbol_occurrences')}
    for x in dedup.execute('SELECT * FROM work_item_members'):
        members[x['work_item_id']].append(occurrences[x['occurrence_id']])
    reserved = {x[0] for x in dedup.execute('SELECT occurrence_id FROM carryover_reservations')}
    active = {x[0] for x in dedup.execute("SELECT m.occurrence_id FROM work_claims c JOIN work_item_members m ON m.work_item_id=c.work_item_id WHERE c.state='active'")}
    compiled = set()
    archives = sorted((root/'temp/core-upstream/root-integration-01').glob('libpresonus*.a'))
    if not archives:raise ValueError('Canonical archives missing')
    for archive in archives:
        result = subprocess.run(['nm','--defined-only','--just-symbols',str(archive)], text=True, capture_output=True, check=True)
        names = result.stdout.splitlines()
        if not any(name.startswith('_Z') for name in names):raise ValueError('No canonical C++ symbols: '+str(archive))
        compiled.update(names)
    native_to_occ = defaultdict(list)
    for o in occurrences.values():native_to_occ[o['native_id']].append(o)
    candidates, parked, counts = [], [], Counter()
    observations = {x['occurrence_id']:dict(x) for x in dedup.execute('SELECT * FROM dependency_observations')}
    for w in dedup.execute("SELECT * FROM reconstruction_work_items WHERE work_kind='reconstruct' AND status='todo'"):
        ms = members[w['id']]
        reasons = eligibility(ms,catalog,admitted,active,reserved,compiled)
        if not ms:reasons.append('no_original_members')
        if reasons:
            counts.update(reasons);parked.append({'work_item_id':w['id'],'reasons':reasons});continue
        rep = occurrences[w['representative']]
        if not rep['demangled'].startswith('Presonus::'):
            counts['outside_application_method_scope'] += 1;continue
        task = catalog[rep['catalog_anchor']]
        obs = observations.get(rep['id'], {})
        if obs.get('coverage') != 'complete static instruction ranges':
            counts['incomplete_native_coverage'] += 1;continue
        body = native.execute('SELECT payload FROM bodies WHERE id=?',(rep['native_id'],)).fetchone()
        if not body:
            counts['missing_native_body'] += 1;continue
        payload = json.loads(body[0])
        if not payload.get('instructions'):
            counts['empty_native_body'] += 1;continue
        target = {'original_elf_sha256':rep['elf_sha256'],'mangled':rep['original_mangled'],'address':rep['original_address'],'size':rep['original_size']}
        observed = collect(native,[target],native_identities)
        edges = list(observed.values())
        boundaries=[]; missing=[]
        for edge in edges:
            targets=native_to_occ.get(edge.get('destination'),[])
            available=[o for o in targets if (o['elf_sha256'],o['original_mangled']) in admitted or o['original_mangled'] in compiled or o['strategy']=='external_source']
            b={'kind':edge['kind'],'native_id':edge.get('destination'),'site':edge['site'],'target_names':[o['demangled'] for o in targets],'available_originals':[o['id'] for o in available]}
            boundaries.append(b)
            if not available:missing.append(b)
        scope=rep['demangled'].split('(')[0].rsplit('::',1)[0]
        candidates.append({'work_item_id':w['id'],'scope':scope,'target':{**rep,'role':task['role'],'firmware':task['firmware']},'covered_originals':[{'anchor':m['catalog_anchor'],'elf':m['elf_sha256'],'mangled':m['original_mangled']} for m in ms],
           'catalog_revision':task['revision'],'dependency_coverage':obs['coverage'],'dependency_blockers':json.loads(obs.get('blockers','[]')),
           'native_body_sha256':hashlib.sha256(body[0].encode()).hexdigest(),'direct_boundaries':boundaries,'missing_direct_boundaries':missing,
           'implementation_readiness':'requires_reviewed_bounded_contract_and_fresh_packet',
           'rank': [len(missing),len(boundaries),rep['original_size']]})
    candidates.sort(key=lambda x:(x['rank'],x['scope'],x['target']['original_mangled']))
    if native_path.stat() != stat_before:raise ValueError('Native database changed during preflight')
    for db in (registry,dedup,native):db.close()
    return enrich_reserve({'version':1,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(), 'dispatch_authorized':False,
      'source_order':'current operational catalog/readiness/history -> unique-work member claims/reservations -> canonical nm -> retained native boundary preflight -> Root reviewed contract -> fresh Memgraph packet',
      'sources':{'registry':manifest['database']['path'],'dedup':dedup_manifest,'native':native_manifest,'archives':[str(p.relative_to(root)) for p in archives]},
      'counts':{'eligible_for_contract_review':len(candidates),'shortlist':min(limit,len(candidates)),'parked_work_items':len(parked),'excluded_reasons':dict(counts)},
      'candidates':candidates[:limit],'parked':parked,
      'required_before_dispatch':['Root-reviewed bounded declaration/state/lifecycle/provider contract with actual oracle plan; missing owned dependencies may be included explicitly','Canonical owned/read files and complete cross-worker write/read conflict check','fresh select_context prepare and batch-dispatch; never reuse stale graph generation','zero unexplained workspace read-input hash mismatch'],
      'rolling_policy':{'blocked':'append original identity, reason, evidence, retry condition; immediately select replacement without restarting unrelated work','completed':'review hash-bound handoff and accept independently; compatible integration/admission may proceed before remaining queue completes'}})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[3])
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--limit',type=int,default=300)
    args=parser.parse_args()
    if args.limit<1:parser.error('limit must be positive')
    report=preflight(args.root.resolve(),args.limit)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report['counts']))

if __name__=='__main__':main()
