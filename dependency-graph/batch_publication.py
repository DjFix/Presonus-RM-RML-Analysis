"""Bounded commits with an atomic server cursor; immutable SQLite is the journal."""
import json
import re
import time
from context_runtime import ContextError, sha

PHASES = ('nodes', 'old_edges', 'new_edges', 'orphan_nodes')


def kind_name(value):
    if not re.fullmatch('[A-Za-z_][A-Za-z_0-9]*', value):
        raise ContextError('Invalid label/relationship kind')
    return value


def apply_rows(tx, phase, rows):
    if phase == 'nodes':
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


def publish(session, database, path, log_path, batch_size=1000, stop_after=None):
    if not 1<=batch_size<=5000:raise ContextError('Batch size out of bounds')
    legacy=database.execute('SELECT value FROM settings WHERE key="replace_legacy_build"').fetchone()
    if not legacy or int(legacy[0]):raise ContextError('Global legacy deletion is not supported by batch publisher')
    digest=sha(path)
    checkpoint='source-delta:'+digest
    existing=session.run('MATCH(p:PublicationCheckpoint {id:$id}) RETURN p.digest AS digest,p.batch_size AS batch_size',id=checkpoint).single()
    if existing and (existing['digest']!=digest or existing['batch_size']!=batch_size):
        raise ContextError('Publication checkpoint mismatch')
    if not existing:
        with session.begin_transaction() as tx:
            n=tx.run('MATCH(g:ContextGeneration {id:"active"}) SET g.state="refreshing" '
                     'RETURN count(g) AS n').single()['n']
            if n!=1:raise ContextError('Missing/duplicate active generation')
            tx.run('CREATE(p:PublicationCheckpoint {id:$id,digest:$digest,batch_size:$size,phase:0,last_row:0,commits:0,state:"publishing"})',
                   id=checkpoint,digest=digest,size=batch_size).consume()
            tx.commit()
    committed=0
    with log_path.open('a') as log:
        while True:
            record=session.run('MATCH(p:PublicationCheckpoint {id:$id}) RETURN p.phase AS phase,p.last_row AS last_row,p.commits AS commits',id=checkpoint).single()
            phase_index,last=int(record['phase']),int(record['last_row'])
            if phase_index==len(PHASES):break
            phase=PHASES[phase_index]
            rows=[dict(row) for row in database.execute('SELECT rowid AS journal_row,* FROM '+phase+' WHERE rowid>? ORDER BY rowid LIMIT ?',(last,batch_size))]
            next_phase=phase_index if rows else phase_index+1
            next_row=rows[-1]['journal_row'] if rows else 0
            start=time.perf_counter()
            with session.begin_transaction() as tx:
                if rows:apply_rows(tx,phase,rows)
                n=tx.run('MATCH(p:PublicationCheckpoint {id:$id}) WHERE p.phase=$phase AND p.last_row=$last '
                         'SET p.phase=$next_phase,p.last_row=$next_row,p.commits=p.commits+1 RETURN count(p) AS n',
                         id=checkpoint,phase=phase_index,last=last,next_phase=next_phase,next_row=next_row).single()['n']
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
    return {'checkpoint':checkpoint,'delta_sha256':digest,'batch_size':batch_size}
