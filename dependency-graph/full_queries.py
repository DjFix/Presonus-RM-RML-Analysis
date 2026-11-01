"""Small, explicit query catalog shared by both graph services and SQLite."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Query:
    sql: str
    cypher: str
    question: str


def direct(kinds, reverse=False):
    kinds = tuple(kinds)
    literals = ','.join("'" + k + "'" for k in kinds)
    types = '|'.join(kinds)
    source, target = ('dst', 'src') if reverse else ('src', 'dst')
    pattern = '(seed)<-[:' + types + ']-(n)' if reverse else '(seed)-[:' + types + ']->(n)'
    return ('SELECT DISTINCT ' + target + ' AS id FROM edges WHERE ' + source +
            '=:seed AND kind IN (' + literals + ') ORDER BY id',
            'MATCH (seed:Artifact {id:$seed}) MATCH ' + pattern + ' RETURN DISTINCT n.id AS id ORDER BY id')


CALL_KINDS = ('CALLS', 'GCC_CALLS', 'ALIAS_OF')
CONTEXT_KINDS = CALL_KINDS + ('USES_DATA', 'GCC_REFERENCES', 'USES_TYPE', 'HAS_TYPE', 'MEMBER_OF', 'INHERITS')
QUERIES = {}
for name, kinds, reverse, question in (
    ('callees', CALL_KINDS, False, 'What does this function call, including compiler aliases?'),
    ('callers', CALL_KINDS, True, 'Which functions call this function?'),
    ('references', CALL_KINDS + ('FUNCTION_REFERENCE', 'GCC_REFERENCES'), True,
     'Which code or static data references it, including address references?'),
    ('context_step', CONTEXT_KINDS, False, 'Which code/type/data dependencies form its reading context?'),
    ('source_files', ('DECLARED_IN', 'IMPLEMENTED_IN'), False, 'Where are the declarations and implementations?'),
    ('unresolved', ('VIRTUAL_CALL', 'INDIRECT_CALL', 'GCC_UNRESOLVED'), False, 'Which dispatch boundaries remain unresolved?'),
    ('overrides', ('OVERRIDES',), True, 'Which observed overrides are potential implementations?'),
    ('fixtures', ('USES_FIXTURE',), False, 'Which explicit input fixtures does this test use?'),
    ('proofs', ('VALIDATED_BY',), False, 'Which validation documents belong to this original record?'),
):
    sql, cypher = direct(kinds, reverse)
    QUERIES[name] = Query(sql, cypher, question)

QUERIES['tests'] = Query('''SELECT DISTINCT t.src AS id
FROM edges t JOIN edges d ON d.src=t.dst JOIN edges call ON call.src=d.dst
WHERE t.kind='HAS_TEST_TU' AND d.kind='DEFINES_FUNCTION'
AND call.kind IN ('CALLS','GCC_CALLS') AND call.dst=:seed ORDER BY id''',
'''MATCH (test:Test)-[:HAS_TEST_TU]->(tu)-[:DEFINES_FUNCTION]->(caller)
MATCH (caller)-[:CALLS|GCC_CALLS]->(:Artifact {id:$seed})
RETURN DISTINCT test.id AS id ORDER BY id''', 'Which current test translation units directly exercise this function?')


def sql_closure(connection, seed, context=False, reverse=False):
    kinds = CONTEXT_KINDS if context else CALL_KINDS
    literals = ','.join("'" + k + "'" for k in kinds)
    source, target = ('dst', 'src') if reverse else ('src', 'dst')
    return {r[0] for r in connection.execute('''WITH RECURSIVE reachable(id) AS (
      SELECT :seed UNION SELECT e.''' + target + ''' FROM edges e JOIN reachable r
      ON e.''' + source + '''=r.id WHERE e.kind IN (''' + literals + '''))
      SELECT id FROM reachable''', {'seed': seed})}


def graph_closure(session, seed, context=False, reverse=False):
    """Portable node-global traversal. Cypher path enumeration is not equivalent."""
    query = QUERIES['context_step' if context else 'callers' if reverse else 'callees'].cypher
    # Batch each frontier into one Bolt request; never enumerate every possible path.
    query = 'UNWIND $frontier AS input\n' + query.replace('$seed', 'input')
    visited = {seed}
    frontier = [seed]
    while frontier:
        found = {r['id'] for r in session.run(query, frontier=frontier)} - visited
        visited.update(found)
        frontier = sorted(found)
    return visited
