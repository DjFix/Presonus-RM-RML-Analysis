"""Project immutable ELF SQLite observations into a separate Memgraph namespace."""
import json
import pathlib
import re
import sqlite3
from neo4j import GraphDatabase
from memgraph_endpoint import memgraph_uri
from context_runtime import sha
from native_context import open_index

ROOT=pathlib.Path(__file__).resolve().parents[1]


def batches(cursor,size=500):
    while True:
        rows=cursor.fetchmany(size)
        if not rows:return
        yield [dict(r) for r in rows]


def main():
    c,pointer=open_index(ROOT)
    driver=GraphDatabase.driver(memgraph_uri(ROOT),auth=None)
    with driver.session() as s:
        s.run('MERGE(g:NativeGeneration {id:"active"}) SET g.state="refreshing"').consume()
        s.run('MATCH(n:NativeArtifact) DETACH DELETE n').consume()
        s.run('CREATE INDEX ON :NativeArtifact(id)').consume()
        for rows in batches(c.execute('SELECT * FROM nodes')):
            for row in rows:
                meta=json.loads(row['metadata']);row.update(mangled=meta.get('mangled'),firmware=meta.get('firmware'))
                resolution=c.execute('SELECT * FROM symbol_resolution WHERE symbol_id=?',(row['id'],)).fetchone()
                row['resolution']=json.dumps(dict(resolution)) if resolution else None
            s.run('UNWIND $rows AS row CREATE(n:NativeArtifact {id:row.id,kind:row.kind,label:row.label,elf:row.elf,firmware:row.firmware,mangled:row.mangled,metadata:row.metadata,resolution:row.resolution})',rows=rows).consume()
        for kind, in c.execute('SELECT DISTINCT kind FROM edges'):
            if not re.fullmatch('[A-Z_]+',kind):raise ValueError(kind)
            for rows in batches(c.execute('SELECT * FROM edges WHERE kind=?',(kind,))):
                result=s.run('UNWIND $rows AS row MATCH(a:NativeArtifact {id:row.src}),(b:NativeArtifact {id:row.dst}) '
                            'CREATE(a)-[:'+kind+' {site:row.site,metadata:row.metadata}]->(b) RETURN count(*) AS n',rows=rows).single()['n']
                if result!=len(rows):raise ValueError('Missing native endpoints')
        count=s.run('MATCH(n:NativeArtifact) RETURN count(n) AS n').single()['n']
        edges=s.run('MATCH(:NativeArtifact)-[r]->(:NativeArtifact) RETURN count(r) AS n').single()['n']
        assert count==c.execute('SELECT count(*) FROM nodes').fetchone()[0]
        assert edges==c.execute('SELECT count(*) FROM edges').fetchone()[0]
        s.run('MATCH(n:NativeArtifact),(f:Function) WHERE n.mangled IS NOT NULL AND n.mangled=f.mangled '
              'CREATE(n)-[:NATIVE_SOURCE_CANDIDATE {basis:"encoded name only; not ABI proof"}]->(f)').consume()
        s.run('MATCH(g:NativeGeneration {id:"active"}) SET g.state="ready",g.digest=$digest',digest=pointer['sha256']).consume()
    receipt={'generation':pointer['sha256'],'nodes':count,'edges':edges,'exact_counts_match':True}
    (ROOT/pathlib.Path(pointer['database']).parent/'memgraph-publication.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt));c.close();driver.close()


if __name__=='__main__':main()
