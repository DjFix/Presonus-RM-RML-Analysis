// Isolated EMPTY experiment database only. Copy exported CSVs to its import dir.
// Execute each statement separately. No connection to operational registry.
CREATE CONSTRAINT experiment_node_id IF NOT EXISTS
FOR (n:Artifact) REQUIRE n.id IS UNIQUE;

LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' AS row
CREATE (:Artifact {id: row.id, kind: row.kind, label: row.label,
                   metadata: row.metadata});

LOAD CSV WITH HEADERS FROM 'file:///edges.csv' AS row
MATCH (s:Artifact {id: row.src}), (d:Artifact {id: row.dst})
CREATE (s)-[:DEPENDS_ON {kind: row.kind, evidence: row.evidence}]->(d);

// Immediate impact, with evidence. Set $id to a file:repository/relative/path.
MATCH (s:Artifact)-[r:DEPENDS_ON]->(d:Artifact {id: $id})
WHERE r.kind IN $kinds
RETURN s.id, r.kind, r.evidence ORDER BY s.id;

// Full reachability benchmark requires node-global visited semantics.
// Do not substitute unrestricted path enumeration for the SQLite closure.
// Implement client BFS with the immediate-impact query above, deduplicating IDs
// across the whole traversal; include round-trip cost in that measurement.
