# Production graph update stop — 2026-11-25

Explicit user instruction stops production derived-graph updates. The maintained
policy is `PRODUCTION_GRAPH_STOP.json`, enforced by `production_write_stop.py`.
There is no environment/CLI override. Removing the policy does not reopen the
canonical checkout. Reopening requires a new explicit instruction and reviewed
code/policy change. SQLite readiness/admission is separate and remains available.

Guards reject before production connection, writer lock creation or staging:

- `refresh_graph.ensure_fresh`, CLI refresh/resume, production Docker launches;
- `refresh_publish.main`, `context_selector.register`, writer-locked entrypoints;
- native index build/publish and candidate lifecycle reconciliation;
- direct Bolt/full imports, identity migration and mutating benchmark commands;
- source index connects, compact migration and publication journals targeting
  canonical `dependency-graph/state` or refresh storage.

The live dedicated Memgraph publication integration script is also stopped.
Pure helpers using fake sessions and isolated SQLite files remain testable.
Read-only graph diagnostics are not globally disabled. This is a project workflow
interlock, not a server ACL against arbitrary external Cypher or historical copied
programs. No CT was stopped and no graph data/journal/capture was removed.

Operational census found no active graph publisher/resume/extract containers.
Packets stopped the legacy Modal successor service/timer, verified MainPID zero,
coordinator gone and exact capture containers absent; partial snapshot and claims
were retained. These were transient systemd-run units without persisted enablement
or restart policy. Unrelated read-only monitoring services were left alone.

Offline verification (no real graph driver requests):

```
uc-library/.venv/bin/python -m unittest discover -s dependency-graph -p test_production_write_stop.py
uc-library/.venv/bin/python -m unittest discover -s dependency-graph -p test_batch_publication_budget.py
uc-library/.venv/bin/python -m unittest discover -s dependency-graph -p test_compact_facts.py
uc-library/.venv/bin/python -m unittest discover -s dependency-graph -p test_publication_budget.py
```

Results: 6 stop regressions, 8 fake-session publication tests, 21 isolated compact
facts tests and 10 budget tests passed. Driver sentinel fails any attempted graph
connection in stop tests. Production stop is checked even if policy is missing or
an environment variable requests writes. Fixture roots without policy are allowed.
