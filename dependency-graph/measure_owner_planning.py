"""Compare exact storage-row planning on real owner facts without database writes.

The two local edits are explicit in-memory benchmark scenarios, not reconstructed
source or a replay of a historical publication. Both planners see one RO snapshot.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import time

ROOT=Path(__file__).resolve().parents[1]


def module(path,name):
    path=(ROOT/path).resolve()
    if not path.is_relative_to(ROOT):raise ValueError('Trusted project-local producer required')
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);sys.modules[name]=value;spec.loader.exec_module(value)
    return value,hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',required=True)
    parser.add_argument('--candidate',default='dependency-graph/compact_facts.py')
    parser.add_argument('--owner',default='@build')
    parser.add_argument('--out',required=True)
    args=parser.parse_args();out=(ROOT/args.out).resolve()
    if not out.is_relative_to(ROOT/'temp/recovery-work'):raise ValueError('Recovery output required')
    out.mkdir(parents=True,exist_ok=False)
    reference,old_hash=module(args.reference,'planning_reference')
    candidate,new_hash=module(args.candidate,'planning_candidate')
    c=sqlite3.connect((ROOT/'dependency-graph/state/refresh-index.sqlite').as_uri()+'?mode=ro',uri=True)
    c.execute('PRAGMA query_only=ON');c.execute('BEGIN')
    nodes={key:{'kind':kind,'label':label,'metadata':json.loads(metadata)}
           for key,kind,label,metadata in c.execute('SELECT id,kind,label,metadata FROM node_facts WHERE owner=?',(args.owner,))}
    edges=set(c.execute('SELECT src,dst,kind,evidence FROM edge_facts WHERE owner=?',(args.owner,)))
    if not nodes or not edges:raise ValueError('Nonempty real owner required')
    key=sorted(nodes)[0];edge=sorted(edges)[0]
    changed_nodes=dict(nodes);changed_nodes[key]=dict(nodes[key],label=nodes[key]['label']+' [planning benchmark]')
    replacement=(*edge[:3],edge[3]+' [planning benchmark]')
    changed_edges=(edges-{edge})|{replacement}
    cases=[('noop',nodes,edges,set(),set()),('one_node',changed_nodes,edges,{key},set()),
           ('one_edge',nodes,changed_edges,set(),{edge,replacement})]
    result={'owner':args.owner,'node_count':len(nodes),'edge_count':len(edges),
            'reference_sha256':old_hash,'candidate_sha256':new_hash,'database_writes':0,
            'scope':'Read-only plan of unchanged real owner and explicit in-memory local edits; excludes mutations', 'cases':[]}
    for name,current_nodes,current_edges,node_changes,edge_changes in cases:
        outputs=[];timings=[]
        for implementation in (reference,candidate):
            count=[0]
            def trace(statement):count[0]+=1
            c.set_trace_callback(trace);start=time.perf_counter()
            try:plan=implementation.CompactFacts(c).plan_owner_rows(args.owner,current_nodes,current_edges,node_changes,edge_changes)
            finally:c.set_trace_callback(None)
            timings.append({'seconds':time.perf_counter()-start,'sql_statements':count[0]});outputs.append(plan)
        if outputs[0]!=outputs[1]:raise ValueError('Storage row plan changed: '+name)
        result['cases'].append({'case':name,'before':timings[0],'after':timings[1],
                                'identical_plan':True,'plan':outputs[0]})
        (out/'progress.json').write_text(json.dumps(result,indent=2)+'\n')
    c.close()
    (out/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
