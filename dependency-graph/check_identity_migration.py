"""Offline v2 identity rehearsal from retained observations; never publishes/activates."""
import argparse
import json
import pathlib
import sqlite3
import time
from code_identity import VERSION, context_id, normalize_ast, owner_id
from context_runtime import sha
from gcc_source_graph import parse_dump
from refresh_facts import connect, facts, replace

ROOT = pathlib.Path(__file__).resolve().parents[1]


def build(entries, out, label):
    folder=out/label;folder.mkdir()
    c=connect(folder/'index.sqlite')
    aliases=[];seen={};inputs={}
    for i,(old_owner,row,ap,gp) in enumerate(entries):
        raw=json.loads(ap.read_text());gcc=json.loads(gp.read_text())
        ast,mapping=normalize_ast(ROOT,row,raw)
        # Reparse historical raw dumps with the same parser on both sides. This
        # separates parser coverage migration from code/identity changes.
        dump=pathlib.Path(gcc['dump'])
        if sha(dump)!=gcc['dump_sha256']:raise ValueError('Raw dump changed: '+str(dump))
        gcc['symbols']=parse_dump(dump.read_text())
        owner=owner_id(ROOT,old_owner.split(':')[0],row)
        if owner in seen:raise ValueError('Duplicate context needs explicit review: '+owner)
        seen[owner]=str(ap)
        dest=folder/owner.replace(':','-');dest.mkdir()
        na,ng=dest/'ast.json',dest/'gcc.json'
        na.write_text(json.dumps(ast)+'\n');ng.write_text(json.dumps(gcc)+'\n')
        nodes,edges=facts(ROOT,owner,row,na,ng)
        replace(c,owner,row,nodes,edges,raw['input_sha256'],na,ng,raw.get('external_inputs',[]))
        # Keep exact legacy bytes, parser identity and lineage in append-only
        # observations, not in logical edge keys.
        lineage={'old_owner':old_owner,'new_owner':owner,'old_ast':str(ap),
                 'old_ast_sha256':sha(ap),'old_gcc':str(gp),'old_gcc_sha256':sha(gp),
                 'raw_dump':str(dump),'raw_dump_sha256':sha(dump),'aliases':mapping}
        aliases.append(lineage)
        for path,digest in raw['input_sha256'].items():
            path=str(pathlib.Path(path).resolve())
            if path in inputs and inputs[path]!=digest:raise ValueError('Mixed input hashes: '+path)
            inputs[path]=digest
        if i%50==0:
            c.commit();print(label,i,len(entries),flush=True)
    c.execute('INSERT INTO meta VALUES(?,?)',('identity_version',str(VERSION)));c.commit()
    (folder/'lineage.json').write_text(json.dumps(aliases,indent=2)+'\n')
    c.execute('CREATE TABLE logical_edges AS SELECT DISTINCT src,dst,kind,evidence FROM edge_facts')
    c.execute('CREATE UNIQUE INDEX logical_edge_keys ON logical_edges(src,dst,kind,evidence)');c.commit()
    result={'contexts':len(entries),'logical_edges':c.execute('SELECT count(*) FROM logical_edges').fetchone()[0],
            'observations':c.execute('SELECT count(*) FROM observations').fetchone()[0],
            'inputs_changed_now':[p for p,h in inputs.items() if not pathlib.Path(p).is_file() or sha(p)!=h]}
    assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    c.close();(folder/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=pathlib.Path,required=True)
    p.add_argument('--run',type=pathlib.Path,required=True)
    p.add_argument('--pairs',type=pathlib.Path,required=True)
    args=p.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    if not out.is_relative_to(ROOT/'temp'):raise ValueError('Output must be project temp')
    start=time.perf_counter();pairs=json.loads(args.pairs.read_text())['pairs']
    rows=dict(json.loads((args.run/'units.json').read_text()))
    previous=[(x['new_owner'],rows[x['new_owner']],ROOT/x['old_ast'],pathlib.Path(x['old_gcc'])) for x in pairs]
    current=[(owner,row,args.run/'observations'/owner.replace(':','-')/'ast.json',args.run/'observations'/owner.replace(':','-')/'0000.json') for owner,row in rows.items()]
    summaries={'previous':build(previous,out,'previous'),'current':build(current,out,'current')}
    c=sqlite3.connect(out/'comparison.sqlite')
    for label in ('previous','current'):
        c.execute('ATTACH DATABASE ? AS '+label,((out/label/'index.sqlite').as_uri()+'?mode=ro',))
    counts={}
    for a,b in [('previous','current'),('current','previous')]:
        counts[a+'_only']={r[0]:r[1] for r in c.execute(f'''SELECT kind,count(*) FROM {a}.logical_edges a
          WHERE NOT EXISTS(SELECT 1 FROM {b}.logical_edges b WHERE a.src=b.src AND a.dst=b.dst
          AND a.kind=b.kind AND a.evidence=b.evidence) GROUP BY kind''')}
    counts['removed']=sum(counts['previous_only'].values());counts['added']=sum(counts['current_only'].values())
    result={'identity_version':VERSION,'summaries':summaries,'delta':counts,'seconds':time.perf_counter()-start,
            'scope':'compiler-owned logical edges; build/global physical migration separate',
            'compiled_units':0,'publication_started':False,'activated':False,
            'producer_sha256':{name:sha(ROOT/'dependency-graph'/name) for name in
                ['code_identity.py','refresh_facts.py','gcc_source_graph.py','check_identity_migration.py']}}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
