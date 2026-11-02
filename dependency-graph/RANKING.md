# Evidence-conservative derived work ranking

`ranking.py` reads the active native/dedup indexes and canonical SQLite records.
It never writes readiness or claims. The policy is `ranking_policy.json`.
This is an initial conservative policy, not an assertion that all dependency
interpretation/research work has been completed. No reconstruction launch follows
from a ranking export alone.

```sh
uc-library/.venv/bin/python dependency-graph/ranking.py build --out temp/recovery-work/dependency-graph/NEW_RANKING
uc-library/.venv/bin/python dependency-graph/check_ranking.py --db temp/recovery-work/dependency-graph/NEW_RANKING/ranking.sqlite --out temp/recovery-work/dependency-graph/NEW_RANKING_CHECK
uc-library/.venv/bin/python dependency-graph/ranking.py explain --db temp/recovery-work/dependency-graph/NEW_RANKING/ranking.sqlite --item EXACT_WORK_ID
uc-library/.venv/bin/python dependency-graph/ranking.py list --db temp/recovery-work/dependency-graph/NEW_RANKING/ranking.sqlite
uc-library/.venv/bin/python dependency-graph/ranking.py reconcile --db temp/recovery-work/dependency-graph/NEW_RANKING/ranking.sqlite
uc-library/.venv/bin/python dependency-graph/ranking.py plan --db temp/recovery-work/dependency-graph/NEW_RANKING/ranking.sqlite --out temp/recovery-work/dependency-graph/NEW_PLAN
uc-library/.venv/bin/python dependency-graph/ranking.py validate-plan --db temp/recovery-work/dependency-graph/NEW_RANKING/ranking.sqlite --plan temp/recovery-work/dependency-graph/NEW_PLAN/PLAN.json --out temp/recovery-work/dependency-graph/NEW_PLAN_RECHECK
```

Build uses a new directory; failed outputs stay available. It checks native input
and full payload hashes, all original memberships, source/dedup generations,
and retains individual native features instead of substituting a representative
for worse group members. A completion marker and static-content digest reject
partial/corrupt indexes. The JSON and Markdown exports contain every work item,
original identity, raw known/unknown/partial feature, reason and rank. The
`original_catalog` table separately retains all catalog occurrences, including
mapping/file symbols and objects without a current unique-work job. Absence of
a work membership never means that an original disappeared or was completed.

Actual work kinds remain distinct. In particular `payload_extraction` completed
does not become `data_interpretation` completed. Function/data/initializer subject
kinds are recorded separately in features. Existing data jobs do not establish
representation/consumer-binding; new typed work must be explicitly justified by
real consumer requirements, rather than invented to satisfy a quota.

The bounded CFG decodes retained instruction bytes in an independently matched
mode, identifies blocks/branches/cycles and rejects unhandled indirect PC writes
as partial. It does not decode Core implementations. Memory operands do not
establish class fields. Register provenance is limited to individual basic blocks,
register moves, immediates, immediate offsets and verified PC-relative literal
words. Calls, joins, decode gaps and conditional writes kill tracked values.
Entry r0 provenance never establishes `this`. A memory access through a tracked
constant can establish a bounded static data address; a matching named-object
extent supplies `data_context` only. `data_binding_behavior` remains unproved.
Anonymous extents block the corresponding context requirement. Relocations and
original declarations remain unknown when not independently established. Vtables and
literal address candidates are not proven dispatch or data-consumer edges.
Initializer effect/order/lifetime requirements remain explicit and unsatisfied.
This initial implementation does not claim a complete ARM value-flow analyzer,
typed data binding, or a complete startup-order analysis.

Rank is lexicographic, within compatible work kinds:

1. Unsatisfied scoped essential requirements.
2. Material uncertainty grade.
3. Semantic complexity grade.
4. Context complexity grade.
5. Unique required dependency targets.
6. Negative count of remaining eligible consumers helped.
7. Stable unique-work ID.

Unknowns are retained as null; unknown grades are 4, not zero. Semantic bins
are expert thresholds, not measured cost: instructions 8/32/128, conditional
branches 0/2/8, blocks 1/4/16. Context dependency bins are 0/2/8. The raw corpus
distribution accompanies every build; the policy is not fitted to a desired
hundred targets. No time, token or money features are used.

Direct calls create separate `callee_context` and `callable_behavior`
requirements. Available original instructions or a hash-verified pinned provider
definition can satisfy context availability for a bounded source port. A header
declaration alone cannot. The generated task must explicitly retain declaration,
layout and boundary uncertainty. Neither a provider name nor a completed claim
nor a declaration-pending implementation satisfies callable behavior automatically.
That behavioral requirement remains unresolved until consumer-specific evidence
is reviewed; reconstruction eligibility is not consumer readiness. The original
v1 policy treated all callable behavior as an essential prerequisite to beginning
reconstruction and therefore excluded every dependency-bearing node. Real-data
validation exposed that conflation; v2 retains both scopes separately. Original
v1 policy and rejected plan remain in trial evidence. Other policy-relative
deficits require research; raising priority is not evidence.

`plan` reconciles canonical routing/claims, checks source freshness and refuses
leaf quota filling. Its output is a planning receipt, **not** `BATCH_DISPATCH.json`.
Even a candidate plan requires exact source ownership, conflict checks, generated
task manifests, ordinary `batch-prepare --jobs auto`, and complete grouped dispatch
before any worker launch. An exact 10×10 deficit never authorizes smaller waves.
A validated index can be advertised by `RANKING_ACTIVE.json`, independently of
whether a reconstruction batch is possible. That pointer is not dispatch or
admission permission; its digest is a publication checkpoint for mutable derived
state. CLI operators use its explicit database path with `--db`.

## Scoped events

```json
{
  "id": "review-unique-id",
  "changes": [{
    "item": "EXACT_TARGET_WORK_ID",
    "expected_revision": "baseline",
    "requirements": [{
      "id": "EXACT_REQUIREMENT_ID",
      "satisfied": true,
      "evidence": {
        "path": "evidence/recovery/REVIEW.json",
        "sha256": "FULL_SHA256",
        "domain": "Exact consumer requirement and bounded verified domain"
      }
    }]
  }]
}
```

Run `ranking.py update --db DB --event EVENT.json` after reviewing the scope.
The operator checks exact target/revision, hash, domain, and boolean state;
it is an attestation operator, not a semantic proof checker. Append-only event
receipts enforce idempotency and rollback on conflicting IDs or stale revisions.
Origins remain separately preserved when current scope evidence changes.
Canonical transactions have no dependency on this derived write succeeding.

Updates revisit affected consumers and suppliers (consumer eligibility affects
supplier help counts). Rank evaluations do not recursively satisfy requirements,
so cyclic requirements remain unsatisfied without explicit external evidence;
the fixed point is reached without letting an SCC confirm itself. A full
`rebuild` reevaluates the complete current scoped state for comparison. Changed
native/source/dedup/policy inputs require a new build; there is no ignore-staleness
override. `build --reuse-db PREVIOUS.sqlite` reuses static native observations
only when the native generation, producer, full static digest and individual
body hashes agree. Current registry/claim routing and every rank are recalculated.
Updates within a build reuse its static tables. `validate-plan` also compares
the full evaluation digest, policy, generation bindings and proposed groups.

`check_ranking.py` verifies real corpus routing and independently rereads sampled
ELF ranges. It applies **synthetic** completion/binding/demotion/interpretation/
claim events only to a separate SQLite backup, comparing every evaluation field
with a full evaluator rebuild. Those synthetic attestations are not native or
provider behavioral evidence and never enter production readiness.

## Completed smaller trial

The user explicitly authorized a smaller validation batch after the exact10x10 deficit. [Trial09 result](../docs/ranked-reconstruction-trial-09.md) records24 compiled-pending identities and4 blockers from28 targets across10 concurrent workers. `RANKING_ACTIVE.json` publishes the derived snapshot; its explicit code-context freshness flag preserves the next-prepare refresh gate after source edits. This is not a second-batch authorization.
