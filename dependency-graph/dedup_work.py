"""Transactional work planning, claims and append-only equivalence review."""
import json
import pathlib
import uuid

from context_runtime import ContextError, inside, sha
from native_context import target_key
from dedup_index import ROOT, add_work, choose, decision, digest, dump, meta, now, verify_inputs


def evidence(refs,root=ROOT):
    if not refs:raise ContextError('Nonempty evidence_refs required')
    for ref in refs:
        if sha(inside(root,ref['path']))!=ref['sha256']:raise ContextError('Evidence changed: '+ref['path'])


def plan(c,task):
    verify_inputs(c)
    originals=task.get('originals')
    if not originals:raise ContextError('Enriched exact originals required')
    work={}; excluded=[]
    for item in originals:
        o=item['original']
        row=c.execute('SELECT * FROM symbol_occurrences WHERE native_id=? AND catalog_anchor=?',(target_key(o),str(o['anchor']))).fetchone()
        if not row:raise ContextError('Original occurrence absent from dedup generation')
        jobs=c.execute('SELECT w.* FROM reconstruction_work_items w JOIN work_item_members m ON m.work_item_id=w.id WHERE m.occurrence_id=? AND w.status!="superseded"',(row['id'],)).fetchall()
        # Payload extraction and provider binding are different work kinds,
        # even when they mention the same original data occurrence.
        requested_kind=task.get('work_kind')
        if requested_kind=='extract_payload':jobs=[j for j in jobs if j['work_kind']=='extract_payload']
        elif row['strategy']=='external_source':jobs=[j for j in jobs if j['work_kind'] in ('provider_binding','provider_adapter')]
        else:jobs=[j for j in jobs if j['work_kind']!='extract_payload' or row['symbol_kind']!='STT_FUNC']
        if len(jobs)!=1:raise ContextError('Ambiguous/missing unique work item')
        job=dict(jobs[0])
        if job['status']=='completed':
            if job['work_kind']=='extract_payload':
                payload=c.execute('SELECT * FROM payload_contents WHERE id=?',(job['subject_id'],)).fetchone()
                file=inside(ROOT,payload['object_path'])
                if file.stat().st_size!=payload['size'] or sha(file)!=payload['content_sha256']:raise ContextError('Previously extracted payload is missing/corrupt; repair explicitly')
            excluded.append({'occurrence':row['id'],'reason':'completed derived work result','work_item_id':job['id']});continue
        if item.get('record') and job['work_kind']=='reconstruct':
            # Existing C++ is evidence to review/reuse, not permission to redo it.
            if task.get('mode')=='reconstruct':
                raise ContextError('Original already has a canonical compiled/ready result; use audit/research with work_kind=review_existing_result')
        if row['strategy']=='external_source' and task.get('mode')=='reconstruct' and task.get('work_kind') not in ('provider_binding','provider_adapter'):
            raise ContextError('external_source requires provider_binding/provider_adapter work; firmware recovery forbidden')
        if job['work_kind']=='resolve_equivalence' and task.get('mode')=='reconstruct':
            raise ContextError('Unresolved equivalence: prepare one research task first: '+job['id'])
        if job['work_kind']=='review_existing_result' and (task.get('mode')=='reconstruct' or task.get('work_kind')!='review_existing_result'):
            raise ContextError('Existing C++ requires explicit audit/research review_existing_result task')
        requested=task.get('work_kind')
        if requested and requested not in (job['work_kind'],'review_existing_result'):
            raise ContextError('Requested work_kind differs from unique queue')
        work[job['id']]=job
    if not work:raise ContextError('All targets already covered; no empty packet')
    if len(work)!=1:raise ContextError('One packet must cover one unique work item; split the task')
    job=next(iter(work.values()))
    members=[dict(r) for r in c.execute('SELECT o.* FROM symbol_occurrences o JOIN work_item_members m ON m.occurrence_id=o.id WHERE m.work_item_id=? ORDER BY o.elf_sha256,o.original_address,o.id',(job['id'],))]
    did=job['decision_id']; d=c.execute('SELECT * FROM equivalence_decisions WHERE id=?',(did,)).fetchone() if did else None
    if d and c.execute('SELECT max(revision) FROM equivalence_decisions WHERE subject_id=?',(d['subject_id'],)).fetchone()[0]!=d['revision']:
        raise ContextError('Work decision superseded; replan required')
    payloads=set()
    for member in members:
        observation=c.execute('SELECT observations FROM dependency_observations WHERE occurrence_id=?',(member['id'],)).fetchone()
        for obs in json.loads(observation[0]) if observation else []:
            payloads.update(x[0] for x in obs.get('payloads',[]))
    selected={str(x['original']['anchor']) for x in originals}
    releases=[dict(r) for r in c.execute('SELECT id,elf_sha256,firmware_version,role,original_path FROM binary_releases ORDER BY id') if r['elf_sha256'] in {m['elf_sha256'] for m in members}]
    result={'generation':meta(c,'generation'),'native_generation':meta(c,'native_generation'),
            'work_item_id':job['id'],'work_kind':job['work_kind'],
            'representative_occurrence':job['representative'],'covered_occurrences':members,'binary_releases':releases,
            'implementation_group_id':job['subject_id'] if c.execute('SELECT 1 FROM implementation_groups WHERE id=?',(job['subject_id'],)).fetchone() else None,
            'equivalence_decision_id':did,'decision_revision':d['revision'] if d else None,
            'verification_scope':d['verification_scope'] if d else None,
            'equivalence_evidence':json.loads(d['evidence_refs']) if d else [],
            'unique_payload_dependencies':[dict(c.execute('SELECT * FROM payload_contents WHERE id=?',(p,)).fetchone()) for p in sorted(payloads)],
            'excluded_duplicate_occurrences':[x['id'] for x in members if x['catalog_anchor'] not in selected],
            'external_provider_bindings':[{'occurrence':x['id'],'provider_id':x['provider_id'],'binding_status':x['binding_status'],'binding':json.loads(x['provider_binding']),'provider':json.loads(c.execute('SELECT metadata FROM external_providers WHERE id=?',(x['provider_id'],)).fetchone()[0])} for x in members if x['strategy']=='external_source'],
            'excluded_completed_targets':excluded,
            'per_occurrence_validation_required':True,'readiness_propagation_allowed':False}
    return result


def claim(c,task,owner,packet):
    if not owner or not packet:raise ContextError('Explicit owner and unique packet path required')
    if c.in_transaction:raise ContextError('Claim requires its own transaction')
    c.execute('BEGIN IMMEDIATE')
    try:
        result=plan(c,task)
        old=c.execute('SELECT * FROM work_claims WHERE work_item_id=? AND state="active"',(result['work_item_id'],)).fetchone()
        if old:
            c.rollback()
            return {'acquired':False,'existing_claim':dict(old),'plan':result}
        ident=uuid.uuid4().hex
        c.execute('INSERT INTO work_claims VALUES(?,?,?,?,?,?,?,?)',(ident,result['work_item_id'],owner,packet,'active',result['generation'],result['equivalence_decision_id'],now()))
        c.execute('INSERT INTO claim_history(claim_id,state,reason,observations,created_at) VALUES(?,?,?,?,?)',(ident,'active','transactional unique claim',dump({'packet':packet}),now()))
        c.commit()
        result['claim_id']=ident;result['claim_owner']=owner;result['claim_packet']=packet
        return {'acquired':True,'plan':result}
    except BaseException:
        c.rollback();raise


def validate_claim(c,binding,packet):
    verify_inputs(c)
    if binding['generation']!=meta(c,'generation'):raise ContextError('Dedup generation changed')
    row=c.execute('SELECT * FROM work_claims WHERE id=?',(binding['claim_id'],)).fetchone()
    if not row or row['state']!='active' or row['owner']!=binding['claim_owner'] or row['packet_path']!=packet or row['work_item_id']!=binding['work_item_id'] or row['generation']!=binding['generation'] or row['decision_id']!=binding['equivalence_decision_id']:
        raise ContextError('Claim is inactive, foreign, or changed')
    job=c.execute('SELECT status FROM reconstruction_work_items WHERE id=?',(row['work_item_id'],)).fetchone()
    if not job or job['status'] in ('completed','superseded'):raise ContextError('Work no longer active')
    if row['decision_id']:
        d=c.execute('SELECT * FROM equivalence_decisions WHERE id=?',(row['decision_id'],)).fetchone()
        revision=c.execute('SELECT max(revision) FROM equivalence_decisions WHERE subject_id=?',(d['subject_id'],)).fetchone()[0]
        if revision!=binding['decision_revision']:raise ContextError('Equivalence revision changed; prepare a new packet')
        evidence(json.loads(d['evidence_refs'])) if json.loads(d['evidence_refs']) else None


def transition(c,claim_id,action,manifest):
    if not manifest.get('reason') or not manifest.get('owner'):raise ContextError('Owner and reason required')
    c.execute('BEGIN IMMEDIATE')
    try:
        row=c.execute('SELECT * FROM work_claims WHERE id=?',(claim_id,)).fetchone()
        if not row or row['state']!='active' or row['owner']!=manifest['owner']:raise ContextError('Only the active owner may finish/release a claim')
        if action=='release':
            if not manifest.get('live_state_checked') or not manifest.get('resumable_state_checked') or not manifest.get('observations'):
                raise ContextError('Release requires explicit process/agent and resumable-state observations; no timeout stealing')
            state='released'
        else:
            verify_inputs(c)
            if row['generation']!=meta(c,'generation'):raise ContextError('Claim generation is stale')
            if row['decision_id']:
                old=c.execute('SELECT subject_id,revision FROM equivalence_decisions WHERE id=?',(row['decision_id'],)).fetchone()
                current=c.execute('SELECT max(revision) FROM equivalence_decisions WHERE subject_id=?',(old['subject_id'],)).fetchone()[0]
                if current!=old['revision']:raise ContextError('Decision changed; cannot accept stale result')
            evidence(manifest.get('evidence_refs'))
            job=c.execute('SELECT * FROM reconstruction_work_items WHERE id=?',(row['work_item_id'],)).fetchone()
            members={r[0] for r in c.execute('SELECT occurrence_id FROM work_item_members WHERE work_item_id=?',(row['work_item_id'],))}
            checks=manifest.get('individual_checks',{})
            if set(checks)!=members or any(not v for v in checks.values()):raise ContextError('Each original occurrence needs its own explicit check domain')
            if job['work_kind']=='resolve_equivalence':raise ContextError('Resolve equivalence through reviewed decision before completing this task')
            if not manifest.get('common_checks'):raise ContextError('Explicit common checks required')
            for member in members:
                occurrence=c.execute('SELECT o.*,r.content_sha256 FROM symbol_occurrences o LEFT JOIN binary_ranges r ON r.id=o.range_id WHERE o.id=?',(member,)).fetchone()
                check=checks[member]
                if not isinstance(check,dict) or check.get('elf_sha256')!=occurrence['elf_sha256'] or check.get('original_mangled')!=occurrence['original_mangled'] or check.get('range_sha256')!=occurrence['content_sha256'] or not check.get('behavioral_domain'):
                    raise ContextError('Per-occurrence ELF, name, full range hash and domain required')
                if job['work_kind']=='reconstruct' and (not occurrence['range_id'] or not occurrence['content_sha256']):
                    raise ContextError('Unknown original extent cannot be accepted as reconstructed')
                if job['work_kind']=='reconstruct' and not check.get('compiled_mangling_checked'):
                    raise ContextError('Original compiled interface checks required per occurrence')
            c.execute('INSERT INTO work_results VALUES(?,?,?,?,?,?,?,?,?)',(uuid.uuid4().hex,row['work_item_id'],dump(sorted(members)),dump(manifest['common_checks']),dump(checks),dump(manifest['evidence_refs']),row['generation'],row['decision_id'],now()))
            c.execute('UPDATE reconstruction_work_items SET status="completed" WHERE id=?',(row['work_item_id'],))
            state='completed'
        c.execute('UPDATE work_claims SET state=? WHERE id=?',(state,claim_id))
        c.execute('INSERT INTO claim_history(claim_id,state,reason,observations,created_at) VALUES(?,?,?,?,?)',(claim_id,state,manifest['reason'],dump(manifest),now()))
        c.commit();return {'claim_id':claim_id,'state':state,'readiness_changed':False}
    except BaseException:c.rollback();raise


def review(c,manifest):
    """Explicit reviewed revision: trust is bounded by hash-bound evidence, not bytes."""
    verify_inputs(c)
    members=sorted(set(manifest['members']))
    status=manifest['status']
    if len(members)<2 or status not in ('verified','rejected','blocked','candidate'):raise ContextError('At least two occurrences and valid status required')
    if manifest['input_generation']!=meta(c,'generation'):raise ContextError('Review generation changed')
    evidence(manifest.get('evidence_refs'))
    rows=[c.execute('SELECT * FROM symbol_occurrences WHERE id=?',(m,)).fetchone() for m in members]
    if any(not r or r['strategy']!='reconstruct' or r['symbol_kind']!='STT_FUNC' for r in rows):raise ContextError('Review applies only to application function occurrences')
    if not manifest.get('reason') or not manifest.get('verification_scope'):raise ContextError('Explicit reason and verification scope required')
    if status=='verified':
        if manifest['verification_scope']!='shared_portable_implementation':raise ContextError('Implementation verification scope must be explicit')
        required=('machine_context','ranges','interfaces','calls','data_payloads','indirect_boundaries','coverage')
        if any(not manifest.get('checks',{}).get(k) for k in required):raise ContextError('Explicit per-domain dependency/interface review required')
        if set(manifest.get('per_occurrence_checks',{}))!=set(members):raise ContextError('Every original occurrence requires a review domain')
    if status=='verified':
        for r in rows:
            physical=c.execute('SELECT content_sha256 FROM binary_ranges WHERE id=?',(r['range_id'],)).fetchone()
            if not physical or not physical[0]:raise ContextError('Shared implementation requires independently verified original ranges')
    import sys
    sys.path.insert(0,str(ROOT/'uc-library/tools/registry'))
    import adapter
    with adapter.snapshot(ROOT/'uc-library') as snapshot:
        existing_cpp_keys={(r['elf_sha256'],r['original_mangled']) for r in rows if snapshot.c.execute('SELECT 1 FROM records WHERE elf=? AND mangled=?',(r['elf_sha256'],r['original_mangled'])).fetchone()}
    subject=manifest.get('subject_id') or digest('reviewed-implementation',members)
    c.execute('BEGIN IMMEDIATE')
    try:
        latest=c.execute('SELECT max(revision) FROM equivalence_decisions WHERE subject_id=?',(subject,)).fetchone()[0] or 0
        if manifest.get('expected_revision',0)!=latest:raise ContextError('Optimistic decision revision mismatch')
        jobs=c.execute('SELECT DISTINCT w.id,w.work_kind FROM reconstruction_work_items w JOIN work_item_members m ON m.work_item_id=w.id WHERE m.occurrence_id IN ('+','.join('?'*len(members))+') AND w.status!="superseded"',members).fetchall()
        claims=[]
        for job in jobs:claims.extend(dict(r) for r in c.execute('SELECT * FROM work_claims WHERE work_item_id=? AND state="active"',(job['id'],)))
        if claims:
            c.execute('INSERT INTO planning_conflicts(subject_id,reason,claims,created_at) VALUES(?,?,?,?)',(subject,'Equivalence review overlaps live work; inspect owners, do not cancel',dump(claims),now()))
            c.commit();return {'conflict':True,'claims':claims}
        did=decision(c,subject,'implementation',status,manifest['verification_scope'],manifest['reason'],members,manifest['evidence_refs'])
        for job in jobs:
            existing={r[0] for r in c.execute('SELECT occurrence_id FROM work_item_members WHERE work_item_id=?',(job['id'],))}
            if not existing<=set(members):raise ContextError('Review would split an existing group; include all members')
            c.execute('UPDATE reconstruction_work_items SET status="superseded" WHERE id=?',(job['id'],))
        representative=choose(c,members)
        if status=='verified':
            existing_cpp=bool(existing_cpp_keys)
            group_revision=digest('implementation-group',subject,did)
            c.execute('INSERT INTO implementation_groups VALUES(?,?,?)',(group_revision,did,representative))
            c.executemany('INSERT INTO implementation_members VALUES(?,?)',[(group_revision,m) for m in members])
            kind='review_existing_result' if existing_cpp or any(j['work_kind']=='review_existing_result' for j in jobs) else 'reconstruct'
            wid=add_work(c,kind,group_revision,members,representative,did)
            c.execute('UPDATE reconstruction_work_items SET status="todo",decision_id=? WHERE id=?',(did,wid))
        elif status=='rejected':
            for m in members:
                row=next(r for r in rows if r['id']==m)
                kind='review_existing_result' if (row['elf_sha256'],row['original_mangled']) in existing_cpp_keys else 'reconstruct'
                wid=add_work(c,kind,m,[m],m,did)
                c.execute('UPDATE reconstruction_work_items SET status="todo",decision_id=? WHERE id=?',(did,wid))
        else:
            wid=add_work(c,'resolve_equivalence',subject,members,representative,did)
            c.execute('UPDATE reconstruction_work_items SET status="todo",decision_id=? WHERE id=?',(did,wid))
        c.commit();return {'decision_id':did,'revision':latest+1,'status':status,'readiness_changed':False}
    except BaseException:c.rollback();raise


def active_index(root):
    from dedup_index import connect
    pointer=json.loads((root/'dependency-graph/DEDUP_ACTIVE.json').read_text())
    c=connect(inside(root,pointer['database']),True)
    verify_inputs(c,root)
    if meta(c,'generation')!=pointer['generation']:c.close();raise ContextError('Dedup active pointer differs from database')
    return c,pointer


def claim_task(root,task,packet):
    from dedup_index import connect
    ro,pointer=active_index(root);ro.close()
    packet=str(inside(root,packet).relative_to(root))
    with connect(inside(root,pointer['database'])) as c:
        result=claim(c,task,task['task_id'],packet)
    if not result['acquired']:
        raise ContextError('Work already claimed; reuse existing owner/task: '+dump(result['existing_claim']))
    binding=result['plan'];binding['database']=pointer['database']
    enriched=dict(task,work_binding=binding)
    existing={str(x['original']['anchor']) for x in task['originals']}
    targets=list(task['targets'])
    for member in binding['covered_occurrences']:
        if member['catalog_anchor'] not in existing:
            targets.append({'original_elf_sha256':member['elf_sha256'],'mangled':member['original_mangled'],'anchor':member['catalog_anchor']})
    enriched['targets']=targets
    return enriched


def validate_packet_work(root,packet,path):
    binding=packet.get('work_binding')
    if not binding:raise ContextError('Packet predates unique-work gate; prepare again')
    c,pointer=active_index(root)
    try:
        if binding['database']!=pointer['database']:raise ContextError('Dedup generation switched; prepare again')
        validate_claim(c,binding,path)
        for payload in binding['unique_payload_dependencies']:
            file=inside(root,payload['object_path'])
            if file.stat().st_size!=payload['size'] or sha(file)!=payload['content_sha256']:raise ContextError('Shared payload object changed')
        originals={str(i['original']['anchor']) for i in packet['originals']}
        if originals!={x['catalog_anchor'] for x in binding['covered_occurrences']}:
            raise ContextError('Packet must include every covered original body/identity')
    finally:c.close()


def validate_batch_work(root,packets,paths):
    seen=set()
    for packet,path in zip(packets,paths):
        validate_packet_work(root,packet,path)
        wid=packet['work_binding']['work_item_id']
        if wid in seen:raise ContextError('Duplicate implementation/payload work in batch: '+wid)
        seen.add(wid)


def publish(root,db):
    """Explicit activation. Never abandon live claims or silently reuse old proofs."""
    from dedup_index import connect
    pointer_path=root/'dependency-graph/DEDUP_ACTIVE.json'
    with connect(db,True) as c:
        verify_inputs(c,root)
        pointer={'database':str(db.relative_to(root)),'generation':meta(c,'generation'),'schema_version':meta(c,'schema_version')}
        if c.execute('PRAGMA foreign_key_check').fetchall() or c.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
            raise ContextError('Dedup database integrity failed')
    if pointer_path.exists():
        old=json.loads(pointer_path.read_text())
        if old==pointer:return pointer
        with connect(inside(root,old['database']),True) as c:
            claims=[dict(r) for r in c.execute('SELECT * FROM work_claims WHERE state="active"')]
            if claims:raise ContextError('Cannot switch generation with live claims; inspect/resume owners: '+dump(claims))
            # Completed results are retained in the old generation. Importing a
            # new native generation never declares old results fresh by itself.
        history=pointer_path.parent/'state/dedup-pointers'
        history.mkdir(parents=True,exist_ok=True)
        target=history/(now().replace(':','-')+'.json');target.write_text(dump(old)+'\n')
    temporary=pointer_path.with_suffix('.new')
    temporary.write_text(json.dumps(pointer,indent=2)+'\n');temporary.replace(pointer_path)
    return pointer
