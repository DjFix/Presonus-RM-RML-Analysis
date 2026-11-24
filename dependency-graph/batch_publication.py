"""Bounded commits with an atomic server cursor; immutable SQLite is the journal."""
import json
import re
import time
import pathlib
from publication_budget import PublicationBudget
from context_runtime import ContextError, sha
from publication_events import require_managed_type_labels, verify_pending

PHASES = ('nodes', 'old_edges', 'new_edges', 'orphan_nodes')


CHECKPOINT_QUERY = 'MATCH(p:PublicationCheckpoint {id:$id}) RETURN p.digest AS digest,p.batch_size AS batch_size'
CLEAN_COUNT_QUERY = 'MATCH(n:Artifact) RETURN count(n) AS n'
CURRENT_QUERY = 'MATCH(g:ContextGeneration {id:"active"}) OPTIONAL MATCH(p:PublicationCheckpoint {id:g.publication_checkpoint}) RETURN g.publication_checkpoint AS checkpoint,properties(p) AS p'
REFRESHING_QUERY = 'MATCH(g:ContextGeneration {id:"active"}) SET g.state="refreshing",g.publication_checkpoint=$id RETURN count(g) AS n'
CREATE_CHECKPOINT_QUERY = 'CREATE(p:PublicationCheckpoint {id:$id,digest:$digest,batch_size:$size,phase:0,last_row:0,commits:0,state:"publishing",contract_version:1,verified_commits:0})'
CURSOR_QUERY = 'MATCH(p:PublicationCheckpoint {id:$id}) RETURN p.phase AS phase,p.last_row AS last_row,p.commits AS commits'
ADVANCE_QUERY = 'MATCH(p:PublicationCheckpoint {id:$id}) WHERE p.phase=$phase AND p.last_row=$last AND p.verified_commits=p.commits SET p.phase=$next_phase,p.last_row=$next_row,p.commits=p.commits+1,p.event_phase=$event_phase,p.event_start=$last,p.event_end=$event_end RETURN count(p) AS n'

def kind_name(value):
    if not re.fullmatch('[A-Za-z_][A-Za-z_0-9]*', value):
        raise ContextError('Invalid label/relationship kind')
    return value


def apply_rows(tx, phase, rows):
    if phase == 'nodes':
        # A stable ID changing kind would retain the previous dynamic label.
        # No delta contract currently owns removal of that label, so preserve
        # the prior node and fail closed instead of certifying a mixed kind.
        existing = tx.run('UNWIND $rows AS row MATCH(n:Artifact {id:row.id}) '
                          'RETURN row.id AS id,n.kind AS kind,row.kind AS wanted,labels(n) AS labels', rows=rows)
        for node in existing:
            if node['kind'] is not None and node['kind'] != node['wanted']:
                raise ContextError('Existing node kind change requires reviewed migration: ' + node['id'])
            require_managed_type_labels(node['id'], node['wanted'], node['labels'])
        for row in rows:
            metadata = json.loads(row['metadata'])
            row['mangled'] = metadata.get('mangled')
            row['path'] = metadata.get('path') or metadata.get('source')
        for kind in sorted({row['kind'] for row in rows}):
            label = kind_name({'file':'File','symbol':'OriginalSymbol'}.get(kind,kind))
            tx.run('UNWIND $rows AS row MERGE(n:Artifact {id:row.id}) SET n:' + label +
                   ' SET n.kind=row.kind,n.label=row.label,n.metadata=row.metadata,n.mangled=row.mangled,n.path=row.path',
                   rows=[r for r in rows if r['kind']==kind]).consume()
    elif phase in ('old_edges','new_edges'):
        for kind in sorted({row['kind'] for row in rows}):
            kind_name(kind)
            selected=[r for r in rows if r['kind']==kind]
            if phase=='old_edges':
                tx.run('UNWIND $rows AS row MATCH(s:Artifact {id:row.src})-[r:'+kind+
                       ' {evidence:row.evidence}]->(d:Artifact {id:row.dst}) DELETE r',rows=selected).consume()
            else:
                n=tx.run('UNWIND $rows AS row MATCH(s:Artifact {id:row.src}),(d:Artifact {id:row.dst}) '
                         'MERGE(s)-[:'+kind+' {evidence:row.evidence}]->(d) RETURN count(*) AS n',rows=selected).single()['n']
                if n!=len(selected):raise ContextError('Missing/duplicate edge endpoints: '+kind)
    elif phase=='orphan_nodes':
        tx.run('UNWIND $rows AS row MATCH(n:Artifact {id:row.id}) '
               'OPTIONAL MATCH(n)-[r:ENCODED_NAME_MATCH]->() DELETE r',rows=rows).consume()
        tx.run('UNWIND $rows AS row MATCH(n:Artifact {id:row.id}) WHERE NOT (n)--() DELETE n',rows=rows).consume()
    else:raise ContextError('Unknown publication phase')


def clean_baseline_mode(database):
    row = database.execute('SELECT value FROM settings WHERE key="source_baseline_mode"').fetchone()
    if row is None:
        return False
    if row[0] != 'current_clean_rebuild':
        raise ContextError('Unknown source baseline mode')
    for table in ('old_edges', 'prior_edges', 'orphan_nodes'):
        if database.execute('SELECT 1 FROM ' + table + ' LIMIT 1').fetchone():
            raise ContextError('Clean source journal cannot retract existing records')
    return True


def _publish(session, database, path, log_path, batch_size=1000, stop_after=None, budget=None):
    if not 1<=batch_size<=5000:raise ContextError('Batch size out of bounds')
    legacy=database.execute('SELECT value FROM settings WHERE key="replace_legacy_build"').fetchone()
    if not legacy or int(legacy[0]):raise ContextError('Global legacy deletion is not supported by batch publisher')
    clean_baseline = clean_baseline_mode(database)
    digest=sha(path)
    checkpoint='source-delta:'+digest
    existing=session.run(CHECKPOINT_QUERY,id=checkpoint).single()
    if existing and (existing['digest']!=digest or existing['batch_size']!=batch_size):
        raise ContextError('Publication checkpoint mismatch')
    if not existing:
        with session.begin_transaction() as tx:
            if clean_baseline:
                if tx.run(CLEAN_COUNT_QUERY).single()['n']:
                    raise ContextError('Clean source publication requires empty Artifact namespace')
            current = list(tx.run(CURRENT_QUERY))
            if len(current) != 1:
                raise ContextError('Missing/duplicate active generation or checkpoint')
            previous = current[0]['p']
            if current[0]['checkpoint'] is not None and previous is None:
                raise ContextError('Missing current publication checkpoint')
            if previous and (previous.get('contract_version') != 1 or
                             previous.get('phase') != len(PHASES) or
                             previous.get('last_row') != 0 or
                             previous.get('verified_commits') != previous.get('commits')):
                raise ContextError('Different journal cannot supersede unfinished publication')
            n=tx.run(REFRESHING_QUERY,id=checkpoint).single()['n']
            if n!=1:raise ContextError('Missing/duplicate active generation')
            tx.run(CREATE_CHECKPOINT_QUERY,
                   id=checkpoint,digest=digest,size=batch_size).consume()
            tx.commit()
    committed=0
    with log_path.open('a') as log:
        while True:
            verified = verify_pending(session, database, checkpoint)
            if verified:
                log.write(json.dumps(verified) + '\n'); log.flush()
            record=session.run(CURSOR_QUERY,id=checkpoint).single()
            phase_index,last=int(record['phase']),int(record['last_row'])
            if phase_index==len(PHASES):break
            phase=PHASES[phase_index]
            rows=[dict(row) for row in database.execute('SELECT rowid AS journal_row,* FROM '+phase+' WHERE rowid>? ORDER BY rowid LIMIT ?',(last,batch_size))]
            next_phase=phase_index if rows else phase_index+1
            next_row=rows[-1]['journal_row'] if rows else 0
            start=time.perf_counter()
            with session.begin_transaction() as tx:
                if rows:
                    budget.charge_rows(len(rows))
                    apply_rows(tx,phase,rows)
                n=tx.run(ADVANCE_QUERY,
                         id=checkpoint,phase=phase_index,last=last,next_phase=next_phase,next_row=next_row,event_phase=phase,event_end=next_row if rows else last).single()['n']
                if n!=1:raise ContextError('Concurrent checkpoint update; batch rolled back')
                tx.commit()
            committed+=1
            receipt={'phase':phase,'rows':len(rows),'last_row':next_row,'commit':int(record['commits'])+1,
                     'seconds':time.perf_counter()-start,'time_ns':time.time_ns(),'checkpoint':checkpoint}
            log.write(json.dumps(receipt)+'\n');log.flush()
            if committed%10==0 or not rows:print('publication: '+json.dumps(receipt),flush=True)
            if stop_after is not None and committed>=stop_after:
                raise ContextError('Injected interruption after committed batch')
    # state remains refreshing until caller verifies and registers the generation.
    return {'checkpoint':checkpoint,'delta_sha256':digest,'batch_size':batch_size,'verification_contract':1,'verification_state':'verified'}


def request_envelope(query, parameters):
    return json.dumps({'query': query, 'parameters': parameters}, ensure_ascii=False,
                      sort_keys=True, separators=(',', ':')).encode('utf-8')


class BudgetedRequests:
    """Count JSON request envelopes, NOT Bolt wire/protocol bytes."""
    def __init__(self, target, budget):
        self.target = target
        self.budget = budget

    def run(self, query, parameters=None, **kwargs):
        params = dict(parameters or {})
        params.update(kwargs)
        envelope = request_envelope(query, params)
        self.budget.charge_transfer(envelope)  # Must precede even read requests.
        return self.target.run(query, **params)

    def begin_transaction(self):
        self.budget.observe()
        return BudgetedRequests(self.target.begin_transaction(), self.budget)

    def __enter__(self):
        self.target.__enter__()
        return self

    def __exit__(self, *args):
        return self.target.__exit__(*args)

    def commit(self):
        self.budget.observe()  # Precommit IO check; remote effects are not local IO.
        return self.target.commit()


class _PlanningResult(list):
    def single(self):
        return self[0] if self else None

    def consume(self):
        return None


class _RequestShapeRecorder:
    """Offline request sizes only; synthetic responses are NEVER verification.

    Calling actual apply/verification routines preserves their query grouping,
    metadata augmentation and parameter shapes. Responses merely let those
    routines enumerate requests without a server. This object never publishes,
    emits a verification receipt, or supplies admission evidence.
    """
    def __init__(self, checkpoint):
        self.checkpoint = checkpoint
        self.bytes = 0
        self.requests = 0
        self.event = dict(version=1, commits=0, verified=0, phase=None, start=0, end=0)

    def count(self, query, parameters):
        self.bytes += len(request_envelope(query, parameters))
        self.requests += 1

    def run(self, query, parameters=None, **kwargs):
        params = dict(parameters or {})
        params.update(kwargs)
        self.count(query, params)
        rows = params.get('rows', [])
        if 'p.contract_version AS version' in query:
            return _PlanningResult([dict(self.event)])
        if 'RETURN g.publication_checkpoint AS checkpoint' in query:
            return _PlanningResult([dict(checkpoint=self.checkpoint)])
        if 'SET p.verified_commits=$commit' in query:
            return _PlanningResult([dict(n=1)])
        if 'n.kind AS kind,row.kind AS wanted' in query:
            return _PlanningResult()  # Existing server state cannot affect bytes.
        if 'properties(n) AS props, labels(n) AS labels' in query:
            result = []
            for row in rows:
                meta = json.loads(row['metadata'])
                props = {k: row[k] for k in ('id', 'kind', 'label', 'metadata')}
                props.update(mangled=meta.get('mangled'), path=meta.get('path') or meta.get('source'))
                label = {'file': 'File', 'symbol': 'OriginalSymbol'}.get(row['kind'], row['kind'])
                result.append(dict(id=row['id'], props=props, labels=['Artifact', label]))
            return _PlanningResult(result)
        if 'count(r) AS n' in query:
            return _PlanningResult([dict(journal_row=row['journal_row'],
                                        n=int(self.event['phase'] == 'new_edges')) for row in rows])
        if 'count(DISTINCT n) AS nodes' in query:
            return _PlanningResult([dict(id=row['id'], nodes=0, degree=0, names=0) for row in rows])
        if 'MERGE(s)-[:' in query:
            return _PlanningResult([dict(n=len(rows))])
        if 'MERGE(n:Artifact' in query or 'DELETE r' in query or 'DELETE n' in query:
            return _PlanningResult()
        raise ContextError('Unknown publication planning request shape: ' + query)


def request_forecast(database, batch_size=1000, digest='0' * 64):
    """Exact offline request shapes, never graph execution/verification evidence."""
    if not 1 <= batch_size <= 5000 or not isinstance(digest, str) or not digest:
        raise ContextError('Invalid publication forecast identity/batch size')
    checkpoint = 'source-delta:' + digest
    recorder = _RequestShapeRecorder(checkpoint)
    # Worst-case bootstrap includes the optional empty-namespace check. Existing
    # checkpoints skip creation, but the complete journal remains an upper bound.
    for query, params in ((CHECKPOINT_QUERY, dict(id=checkpoint)), (CLEAN_COUNT_QUERY, {}),
                          (CURRENT_QUERY, {}), (REFRESHING_QUERY, dict(id=checkpoint)),
                          (CREATE_CHECKPOINT_QUERY, dict(id=checkpoint, digest=digest, size=batch_size))):
        recorder.count(query, params)
    bootstrap_bytes = recorder.bytes
    verify_pending(recorder, database, checkpoint)
    recorder.count(CURSOR_QUERY, dict(id=checkpoint))
    rows = payload_bytes = commits = 0
    phase_counts = {}
    for phase_index, phase in enumerate(PHASES):
        cursor = database.execute('SELECT rowid AS journal_row,* FROM ' + phase + ' ORDER BY rowid')
        last = 0
        phase_rows = phase_start = 0
        phase_start_bytes = recorder.bytes
        while True:
            part = [dict(row) for row in cursor.fetchmany(batch_size)]
            phase_start = last
            if part:
                rows += len(part)
                phase_rows += len(part)
                payload_bytes += sum(len(json.dumps(row, ensure_ascii=False,
                                         separators=(',', ':')).encode('utf-8')) for row in part)
                apply_rows(recorder, phase, part)
            next_phase = phase_index if part else phase_index + 1
            next_row = part[-1]['journal_row'] if part else 0
            recorder.count(ADVANCE_QUERY, dict(id=checkpoint, phase=phase_index, last=last,
                           next_phase=next_phase, next_row=next_row, event_phase=phase,
                           event_end=next_row if part else last))
            commits += 1
            recorder.event = dict(version=1, commits=commits, verified=commits-1,
                                  phase=phase, start=phase_start,
                                  end=next_row if part else last)
            verify_pending(recorder, database, checkpoint)
            recorder.count(CURSOR_QUERY, dict(id=checkpoint))
            if not part:
                break
            last = next_row
        phase_counts[phase] = dict(rows=phase_rows, json_request_bytes=recorder.bytes-phase_start_bytes)
    return {'emitted_rows': rows, 'encoded_row_bytes': payload_bytes,
            'json_request_estimate_bytes': recorder.bytes,
            'planning_scope': 'offline complete fresh apply and postcommit verification request envelopes; not execution evidence',
            'planned_json_requests': recorder.requests, 'planned_commits': commits,
            'bootstrap_upper_bound_bytes': bootstrap_bytes, 'phases': phase_counts}


def journal_preflight(database, path, budget, batch_size):
    """Forecast immutable journal with the same apply/verification request logic."""
    size = pathlib.Path(path).stat().st_size
    budget.preflight(journal_estimate_bytes=size, sqlite_write_estimate_bytes=budget.write_bytes,
                     rows=budget.rows, transfer_bytes=budget.transfer_bytes)
    result = request_forecast(database, batch_size, sha(path))
    budget.preflight(journal_estimate_bytes=size, sqlite_write_estimate_bytes=budget.write_bytes,
                     rows=budget.rows + result['emitted_rows'],
                     transfer_bytes=budget.transfer_bytes + result['json_request_estimate_bytes'])
    budget.observe([path])
    return dict(result, journal_actual_bytes=size)


def publish(session, database, path, log_path, batch_size=1000, stop_after=None, budget=None):
    """Publish with finite routine ceilings unless caller supplies explicit mode.

    Checkpoint/cursor and immutable-journal contracts are unchanged. A budget
    failure never implicitly enables full rebuild. A retry uses the same journal
    and server cursor; attempted rows and requests are charged within each run.
    """
    from production_write_stop import require_graph_storage_write
    require_graph_storage_write(path)
    log_path = pathlib.Path(log_path)
    budget_path = log_path.with_name(log_path.name + '.budget.json')
    planning = None
    failure = None
    try:
        if not 1 <= batch_size <= 5000:
            raise ContextError('Batch size out of bounds')
        if budget is None:
            budget = PublicationBudget()
        planning = journal_preflight(database, path, budget, batch_size)
        return _publish(BudgetedRequests(session, budget), database, path, log_path,
                        batch_size, stop_after, budget)
    except BaseException as exc:
        failure = '{}: {}'.format(type(exc).__name__, exc)
        raise
    finally:
        receipt = budget.receipt() if budget is not None else {'version': 1, 'failure': failure}
        receipt.update(publication_failure=failure, publication_preflight=planning,
                       transfer_measurement='UTF-8 JSON serialized query/parameter envelopes; not Bolt wire bytes; excludes responses and transaction-control protocol')
        # One replaceable receipt, never an append-only history or another copy
        # of the journal. Do not mask the original publication exception on an
        # evidence write failure.
        try:
            budget_path.write_text(json.dumps(receipt, indent=2) + '\n')
        except OSError:
            if failure is None:
                raise
