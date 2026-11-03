# Bounded context batches

Batch context preparation is analysis infrastructure. It does not start firmware
reconstruction, change readiness, admit results, or release work claims.

```sh
uc-library/.venv/bin/python uc-library/tools/recovery/select_context.py batch-prepare \
  --tasks temp/recovery-work/TASKS.json --out temp/recovery-work/NEW_BATCH --jobs auto
```

`TASKS.json` contains `{"tasks":["repository/relative/task-a.json", "repository/relative/task-b.json"]}`.
An explicitly authorized smaller trial can set `"allow_smaller": true` and a
nonempty `"smaller_batch_authorization"` in this manifest. Grouped trials then
allow one to ten groups, each with one to ten packets, including unequal sizes.
Without that explicit flag the original exact ten groups of five, ten or twenty rule
remains. Identity, coverage, ownership, claim, source freshness, nonempty packet,
full validation and the complete atomic publication barrier are unchanged.
The standalone group publisher additionally requires `--allow-smaller`.
Each task retains the ordinary exact ELF/name identity, mode, namespace and file
ownership contract. Each packet is in `NEW_BATCH/packets/TASK_ID`, with its own
claim, enriched request, manifest, native context, slices and evidence. Use
`--selection-jobs N` and `--slicing-jobs N` to impose separate stage ceilings.
Numeric `--jobs N` is an upper bound subject to resource safety ceilings.
For grouped preparation add the existing `groups` array (ten groups, five, ten or twenty
`packets` each, `task_name`, `scope_reason`, exact `execution_order`) beside
`tasks`; packet paths must be `NEW_BATCH/packets/TASK_ID`. One worker owns
each group, allowing shared files only within that group.

## Consistency and launch permission

The coordinator takes exclusive `dependency-graph/state/context.lock` for setup:
validate tasks, refresh if necessary, plan unique work, obtain claims and freeze
the generation, input hashes and tools. Refresh time is recorded separately.
Parallel builders take their own shared locks, use independent copies of bound
generation inputs through read-only snapshot overlays, use separate output
directories and retain
one runner and one analysis container for the batch. Generation publication and
supported mutation operators require exclusive locking. Shared locking does not
prevent an external editor from changing files.

After builders finish the coordinator reacquires exclusive locking. It checks
the original generation, source inventory, file hashes, instructions and tools,
selected current registry records, active claims, every packet and ownership /
write-read conflicts. Full validation runs through one environment with a shared
graph session and common immutable generation/tool inputs; final filesystem and
binding checks are fresh. Failure of any required check blocks the entire batch.
No readiness proof is cached or reused. There is no AST cache in this change.

The coordinator hashes each independent source copy before recording its new
filesystem fingerprint. The read-only snapshot receipt is pinned by SHA-256 and
exact generation. A builder uses that stat cache only when `samefile` proves its
canonical input is the independently copied snapshot inode, the expected content
digest agrees with the generation, and the recorded copy fingerprint still
matches. Missing or changed bindings fail or trigger ordinary fresh hashing.
The live host guard cannot use a different snapshot inode to bless changed live
files. Final live inventory/source/hash checks remain mandatory. This is reuse
of verified immutable analysis inputs, not a readiness-proof cache. Environment
variables carrying the receipt are internal container bindings, not an operator
staleness override.

Only `BATCH_DISPATCH.json` with `publication_state: complete` authorizes the batch.
Its publication ID and every context hash must agree with `BATCH_MEMBER.json` in
each packet. Membership files contain no spawn arguments. They may exist before
publication or after a failed publication; that never authorizes a worker.
Batch packets do not receive per-packet `DISPATCH.json`. Standalone dispatch
refuses batch members. Baseline expansion authenticates the common publication.
Ordinary single packet commands still produce their ordinary standalone dispatch.

`group_dispatch.py` retains the ten-worker, five-or-ten-packets-per-worker
interface and now validates all packets in one container before publishing the
same atomic barrier. Within a group one worker may own shared files; inter-group
write/read overlap remains forbidden.

## Resources

`auto` reads CPU affinity, visible ancestor cgroup CPU quotas, host MemAvailable,
and visible ancestor cgroup memory limit minus usage. It caps builders by those
resources and task count, independently of LLM agent counts. Selection/validation
also observe the Memgraph cap (default 4); AST slicing has its own ceiling.
Unknown resource information conservatively selects one builder.

CLI tuning flags are `--memgraph-cap`, `--selection-memory-mib`,
`--slicing-memory-mib` and `--reserve-memory-mib`.

Default planning estimates are 512 MiB for selection/validation, 1536 MiB for AST
slicing, and 1024 MiB reserved host memory. These are configurable estimates,
not measured peak demand or guarantees provided by container limits. Detection,
policy, selected limits and reasons are recorded in each attempt's resources
receipt. Current VM101 affinity permits three CPUs: `auto`, `4` and `8` are
therefore capped at three builders unless its allocated resources change.

## Evidence, interruption and resume

Keep failed outputs. Never release a production claim to benchmark or retry.
Container image IDs are pinned before startup and retained across resume;
Python/library versions and exact image IDs remain in local evidence. Each
container builder holds its own shared lock, including after coordinator death.
A live or uninspectable old environment blocks resume.

An explicit `--resume` uses the same task manifest and frozen generation, verifies
existing claims belong to the exact owner and packet, and preserves completed
packet evidence. No expiry or stealing is introduced. Inspect live coordinator,
container handles and resumable state before retrying. A timeout is not failure.
Partial selection files without a complete manifest, or malformed state, block
automatic resume and require inspection; completed selections/slices/finalizations
and a completed common publication can be safely resumed without overwriting
evidence. Interrupted snapshot copying preserves the partial tree separately.

Attempts, command argv, logs, resource receipts, lock waits, refresh, claim/enrich,
builder stages, graph query metrics, validation and publication evidence are local
under the batch output. Historical producer evidence is not rewritten.

Supported direct graph writers (`import_bolt.py`, `load_full_graph.py`,
`case_last_cycle.py`, `refresh_publish.py`, `native_publish.py`) acquire exclusive locking. Refresh
retains its host exclusive lock across the internal publisher child. Native index
production uses `native_graph.py --out ...` or its compatibility coordinator
`locked_native_graph.py --out ...`; both take exclusive locking. Historical
native reports retain their old producer identities; this CLI change does not
relabel those reports as executions of the changed producer.

## Comparable measurements

`benchmark_context_batch.py` runs real selection, native evidence, AST slicing,
finalization and validation against copied SQLite stores and read-only source
inputs. It never publishes dispatch or launches reconstruction. It compares the
container-per-stage path with persistent environments on the same task inputs.
The measured kernel excludes host refresh, enrichment, claims and dispatch
publication; do not describe its speedup as an end-to-end preparation speedup.
Cold means new process/container, not flushed filesystem or server caches.
Resource samples and query counts are retained; unobserved remote graph CPU and
memory must be reported as unobserved, not estimated from container limits.

Example comparable kernel run (inputs must already name exact existing task
requests; this never authorizes their reconstruction):

```sh
uc-library/.venv/bin/python dependency-graph/benchmark_context_batch.py \
  --out temp/recovery-work/NEW_BENCHMARK \
  --tasks temp/recovery-work/EXISTING_PACKET/request.json \
  --jobs 1 4 8 auto --repeats 2
```

Pipeline wall time includes the new path's immutable snapshot, image pinning and
environment startup. Kernel wall time excludes snapshot preparation separately.
The old path is a container per stage; the new path uses the actual batch
environment and the same selection/slicing/finalization schedule.

## Twenty-target groups and compilation resources

Exact10×20 uses200 distinct one-original work packets. Every existing identity,
unique-work, nonempty, conflict, freshness and atomic publication gate is the
same. `group_dispatch.py --packets-per-worker 20` is supported. The explicit
smaller-batch exception retains its previous maximum10 packets per group; it
is not a way to launch a partial200 trial. Unit/atomic fixture coverage does
not assert that a real200-target reconstruction has run.

Source refresh compiler/AST concurrency now observes affinity, all cgroup CPU
and memory ancestors and current available memory. It leaves one CPU on small
hosts, two on hosts with at least8 CPUs, budgets1.5GiB per job and reserves2GiB.
Docker receives a corresponding bounded CPU/memory budget; the extractor
rechecks actual container constraints before choosing its pool. Unknown limits
force one job. Host/container resource receipts are retained in each refresh.
These estimates do not guarantee peak memory. Publication parameters, source
hashes, actual GCC/Clang replay and all validation gates are unchanged.

### Flexible 200-target trial

`group_dispatch.py --flexible-total 200` permits one to ten simultaneous worker
scopes with one to 25 packets each, exactly 200 packets in total. This mode is
separate from `--allow-smaller`; they cannot be combined. Group sizes may differ.
All original generation, identity, original range, ownership, dependency,
publication and per-packet validation gates still apply. This does not authorize
selecting research-required work or bypassing a candidate deficit.
