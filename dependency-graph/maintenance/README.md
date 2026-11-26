# One maintenance refresh, then stop

Maintained runner: `dependency-graph/maintenance/runner.py`. Runtime CONFIG,
receipts and logs remain under `temp/recovery-work/rolling-c001-20261124/graph-resume01/job/`.
These templates are not installed or running.

Maintained tooling only. Nothing here is installed, enabled or launched. CONFIG.json
is intentionally incomplete: null package scope/receipt/activation hashes prevent
launch. Root owns package acceptance (the required137/171 boundary), source freeze,
current package validation and final commit. Runner does not count readiness or
choose which package is accepted.

After the exact package acceptance+commit and allowed guard-v2 application, Root:

1. Verifies current source freeze and records accepted/committed package boundary
   using the guard-v2 receipt schema; puts BOUNDARY-RECEIPT.json here and hashes it.
2. Stages ACTIVATION-POLICY.json using the explicit guard-v2 maintenance schema,
   same package scope/commit and exact receipt reference. Does not write the live
   policy manually; runner preserves and activates it after all checks.
3. Fills CONFIG package_scope and exact receipt/activation hashes. Rechecks guard,
   refresh and budget source hashes against the actual committed files, and exact
   current stopped policy hash (CONFIG anticipates the reviewed guard-v2 draft).
   Reviews concrete compiler-rescan reason. No full-rebuild/resume/budget override
   or repository/database copy is allowed. Routine limits remain3GiB journal,
   12GiB process SQLite writes,3GiB transfer,30million rows.
4. Reviews/installs the fixed opencs-graph-resume01.service template through the
   authorized service mechanism; starts asynchronously only when ready:

   ```sh
   systemctl --user start --no-block opencs-graph-resume01.service
   systemctl --user show opencs-graph-resume01.service -p MainPID -p ExecMainPID -p InvocationID
   ```

   These commands were not executed. Type=exec, RemainAfterExit=yes, Restart=no;
   no MemoryMax or legacy4GiB cap. STARTED records actual runner PID and systemd
   INVOCATION_ID; exclusive creation prevents any unattended retry. Existing
   STARTED must not be removed merely to rerun a failure. Preserve all outcomes.
5. Uses MONITOR-CONFIG-PROPOSAL paths with the separately owned hourly monitor.
   Binds actual InvocationID from the service/STARTED to monitor CONFIG and records
   actual timer/task ID and schedule. Null expected_invocation_id is not proof
   that an instance is configured or terminal. No scheduler is installed here.

Runner verifies actual git HEAD against receipt commit, exact guard/refresh/budget
hashes, explicit activation policy and exact stopped bytes. It preserves
PRIOR-STOPPED-POLICY.json and invokes exactly the existing Python refresh_graph.py
with --compiler-rescan REASON, attached until it returns. No next cycle follows.
Endpoint/network configuration is existing Root-verified192.168.50.226; runner does
not alter/test it or resume pending journals.

Finally restores exact stopped bytes on refresh success, failure or launch error.
If policy bytes changed by another actor, leaves those foreign bytes untouched,
marks restoration_blocked and exits unsuccessfully. Policy writers must honor
same .maintenance-policy.lock; compare-before-replace is not protection against
an uncooperative writer racing between comparison and rename. Root must inspect
that actionable terminal condition rather than restarting.

Normal SIGTERM/SIGINT requests are logged while the attached refresh continues to
its actual terminal state, then finally restores policy. Unit uses KillMode=process,
SendSIGKILL=no and infinite stop timeout to avoid detaching a live Docker publisher.
SIGKILL, host crash or power loss cannot execute Python finally: preserved receipts
and prior policy require operator recovery, never automatic reopen/retry. Refresh
CLI failure is terminal for this one-shot invocation, not authorization to resume
an old publication. Monitor must surface failure/policy-restoration exceptions.

Offline test command (all invoke calls mocked; no Git, graph, systemd or network):

```sh
uc-library/.venv/bin/python -B -m unittest discover -s dependency-graph/maintenance -p test_runner.py -v
```


The service template is for the user manager (`systemctl --user`); it deliberately
omits User/Group identity switching. Runner/monitor code is maintained under dependency-graph/maintenance; runtime
config, logs and receipts remain in the project temp graph-resume01 tree. ExecStart
uses the maintained script and explicit runtime CONFIG path. No installation or start has been performed.

Atomic writes use exclusive `<target>.new` scratch files. A residue causes the
operation to fail closed; do not delete it or retry automatically. Preserve it,
inspect target bytes and STARTED/STATUS/logs, and let Root resolve the interrupted
write explicitly. A restoration failure is actionable and must not be reported
as a restored stopped policy.


# Graph resume hourly monitor — prepared, not installed

Reserved job: `opencs-graph-resume01.service`. Monitor user units:
`opencs-graph-resume01-monitor.service` and `opencs-graph-resume01-monitor.timer`.
The existing `opencs-rolling-sqlite-status.timer` remains separate and unchanged.

`monitor.py` reads only that exact systemd unit, a20-line journal tail,
at most2 explicit log tails32KiB each, and at most8 explicit progress JSON receipts64KiB each.
It records MainPID, ExecMainPID, InvocationID, start/exit timestamps, exit code/status,
unit Result, inexpensive `/proc/meminfo`, and filesystem capacity. There are no SQLite
reads, graph queries/writes, job start/restart operations, or next-cycle actions.
No directory searches or expanding progress globs are used.

Output: atomic `records/LATEST.json`, UTC snapshots, append-only `records/HOURLY.jsonl`
under a local file lock, and first confirmed `records/TERMINAL.json` retained even if
later observations become unknown. The journal/log excerpts and progress receipt
summaries are observations, not completion authority. This monitor is for one
reserved job invocation; do not reuse its records directory for another run.

Missing/not-loaded unit is explicitly `not_started`. A failed/timed-out systemctl
query is `unknown`, never terminal. Default zero exit fields without an actual exit
are not success. Active/running and activating/deactivating are nonterminal.
An observed terminal result without configured expected InvocationID is
`unbound_finished`/`unbound_failed`, not completion of the requested run.
A different InvocationID is `instance_mismatch`, not completion. Root must bind the
actual fresh job InvocationID in CONFIG.json after launch, preserving its launch receipt.

## Future Root activation (not executed by this preparation)

Only after the user's package acceptance/commit prerequisite and Root launch approval:

1. Review CONFIG.json. Fill only the exact future log/progress receipt paths supplied
   by the graph job owner (empty lists remain valid). Install the two templates as user
   units in `~/.config/systemd/user/`, then `systemctl --user daemon-reload` and
   `systemctl --user enable --now opencs-graph-resume01-monitor.timer`.
2. Verify the REAL schedule and save its output in this monitor directory:
   `systemctl --user show opencs-graph-resume01-monitor.timer -p Id -p ActiveState -p TimersCalendar -p NextElapseUSecRealtime -p LastTriggerUSec`.
   Require ActiveState=active, actual hourly calendar and a future next due within60minutes.
   A template, manual clock check or manual status loop is not an installed schedule.
3. Run the first real monitor service tick:
   `systemctl --user start opencs-graph-resume01-monitor.service`.
   Verify its Result/ExecMainStatus and inspect records/LATEST.json. A not_started tick
   before graph launch is valid evidence of monitor operation, not graph execution.
4. Root alone launches the guarded graph job through its separately reviewed unit.
   Capture `systemctl --user show opencs-graph-resume01.service -p Id -p InvocationID -p MainPID -p ExecMainPID -p ExecMainStartTimestamp -p ActiveState -p SubState`.
   Save this actual launch evidence, put that exact nonempty InvocationID in CONFIG.json,
   then start the monitor service once and verify job_instance_verified=true and that
   the recorded invocation/PID/timestamps match. Do not infer launch from a template.
5. Leave the real hourly monitor timer active after the Codex work stops. Root stops
   before any next production cycle; monitor never resumes or advances work.
   Verify at least the first actual calendar-triggered snapshot/LastTriggerUSec when
   active long enough. Preserve terminal records and all failed query observations.

These units write local status while the chat is dormant. They do not deliver ChatGPT
messages or wake a dormant thread. No ChatGPT scheduling tool is available in this
session. Do not claim that this preparation installed monitoring or guarantees chat
notifications. Root may report the actual retained status on resumption.

## Offline check

`uc-library/.venv/bin/python -B dependency-graph/maintenance/test_monitor.py`

Seven fixture tests exercise missing, query failure, running/transition, success/failure,
old invocation rejection and atomic latest/retained-terminal behavior. They use isolated
scratch directories and never create live records or query a real unit.


Monitor runtime CONFIG and records remain in `temp/recovery-work/rolling-c001-20261124/graph-resume01/monitor/`; no runtime JSON/logs belong in this maintained directory.
