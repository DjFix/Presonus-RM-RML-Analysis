# Migration gate

CT125 bootstrapping is separate from data migration. Root must confirm the local
publisher is idle/stopped and preserve its sealed delta and pending journal.
Do not rerun compiler observations. Do not manually mark generations ready.

Before transfer, record local labels, edge types, indexes and source/native
markers through a real Bolt session. Create a consistency snapshot using
`CREATE SNAPSHOT;`, record the exact returned snapshot path and SHA-256.
Transfer that completed snapshot through VM101 to CT125, keeping old data and
WAL untouched. Stop only the NEW CT database during snapshot placement; verify
matching version 3.13.0 and image UID/GID. Put the completed snapshot under
`/srv/memgraph/data/snapshots/` with its original name and correct owner. Preserve
all preexisting target snapshots and WAL in a dated backup directory before any
restore. Ensure startup recovery is enabled. Start Memgraph, then repeat the
same counts, indexes, edge types, markers and known native/source queries.

Root owns endpoint changes and resuming the existing sealed publication. Do not
remove old containers or volumes. A new empty endpoint or successful RETURN1
alone is not completed migration or publication readiness.

Keep backup copies on VM101 outside the CT data volume, hash them and record
source instance, snapshot name, firmware/source generation metadata and time.
Bound Docker log rotation to 3 x 20MiB per service. Retain persistent Memgraph
logs under `/srv/memgraph/log`; review retention separately before data grows.
