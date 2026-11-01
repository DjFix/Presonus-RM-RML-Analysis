# Reconstruction worker handoff v1

The worker delivers C++, tests, independent oracle fixtures, a replay entry point
and a local proof under its assigned ownership. Root reviews the implementation
and runs the common acceptance command, then retains existing global integration
and guarded readiness admission. This contract does not change registry schemas
or permit proof reuse in place of required fresh checks.

`HANDOFF.json` uses repository-relative paths. It has these fields:

| Field | Required contents |
| --- | --- |
| `version` | `1` |
| `task_id`, `namespace` | Exact dispatched task and owned scope |
| `packet_manifest` | Path to the sealed packet's `context.json`; also bind it in artifacts |
| `originals` | Nonempty array with `elf_sha256`, `firmware`, `role`, `mangled`, `address`, `size`, `section` for every target/variant |
| `artifacts` | Array of `{ "kind": "source", "path": "...", "sha256": "..." }`; include source, test, fixture, replay, proof, packet and relevant dependencies/producers |
| `checks` | Array of `{ "kind": "replay", "argv": ["..."], "timeout_seconds": 120 }`; at least format, compile, symbols, replay |
| `validation_domain` | Nonempty description of inputs, state and observed outputs |
| `limitations` | Explicit unresolved declarations/layout/ABI, stubs and untested paths; use an explicit statement if none |
| `build_integration` | Production partition, public headers, test targets, link dependencies and exact CTest argv/fixture bindings proposed to Root |

Use the actual packet manifest filename produced by prepare (inspect the packet;
do not invent a replacement). All targets must agree with that sealed task.
Root reviews identity agreement and proof substance; the acceptance tool checks
the delivery structure and current hashes, not the truth of scientific claims.

The local proof must bind ELF inputs and each actual range/section/file offset,
oracle/replay producer hashes and versions, formatted source hashes, exact
commands and outcomes, compiled symbols, fixture hashes and case counts. Record
real original executions separately from portable C++ executions. Expected
observations must originate in the original ELF or pinned provider, independently
of reconstructed behavior. Capture relevant memory writes, side effects and
external-call traces as well as return values. Aliases retain separate range
checks. Pseudocode is analysis evidence, never an execution oracle.

Fixtures may be function-specific; the common interface is an argv replay that
returns nonzero on mismatch and logs case count and bounded domain. No common
flat fixture format can faithfully describe every function's memory or calls.
Canonical CTest must invoke this replay against its canonical built executable,
with explicit hash-bound fixtures. The worker supplies the adapter and metadata;
Root should not reverse engineer fixture formats during integration.

Checks run from the repository root, without a shell wrapper. Commands must be
noninteractive and preserve originals, registry, shared CMake and global proofs.
Write intermediate build outputs only to assigned scratch. The format check is
read-only: format before sealing. Repeated compilation may update scratch but
must not alter bound inputs. Root reviews argv and scripts before execution;
this runner executes code and provides no security isolation.

```sh
uc-library/.venv/bin/python uc-library/tools/recovery/accept_worker.py \
  --handoff uc-library/candidates/BATCH-WORKER/HANDOFF.json \
  --out temp/recovery-work/BATCH-WORKER-acceptance-01
```

The output directory must be new. `acceptance.json` and per-command logs retain
timings, argv and failures. Input hashes are rechecked after replay. Exit success
means local checks passed; it never promotes readiness. Root still runs all
existing Linux integration, active-source, formatting, installed-role, mangling,
behavior, mirror and guarded SQLite admission gates. Do not reuse an old success
after input changes. Repair local failures at the worker; do not silently patch
the oracle or weaken a gate.

For the next authorized trial, freeze infrastructure first. Capture provider
cumulative usage before dispatch and after completion for Root and every fresh
worker separately. Record local acceptance and global integration as separate
timed phases, preserving parallel wall time rather than summing overlapping
worker durations. Include failure/retry and reporting costs in total-cycle
metrics. Token collection is coordinator-owned; workers provide session IDs,
phase timestamps and context requests, not estimated model-token counts.
