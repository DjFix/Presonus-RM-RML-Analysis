# ELF context for unreconstructed functions

The context operator now joins the source index with an immutable native SQLite
index and its separate `NativeArtifact` projection in Memgraph. Each target must
have verified original instructions, an actual reconstructed source body, or a
verified pinned external-source definition. Empty packets are rejected in every
mode, including research; `uncertainty_work` cannot override this requirement.

## Identity and versions

`binaries.id` is the full source ELF SHA-256; `firmware`, `role`, original path and
ELF metadata are separate columns. Symbol identity hashes ELF + original mangled
name + address + size + actual section. Original catalog anchors/metadata remain
attached. All 51,137 current catalog identities are retained, including aliases.
Execution and data-reference edges stay within one ELF. `ELF_NAME_CORRESPONDENCE`
across binaries/versions means exact encoded-name equality only, not calls,
behavior equivalence or ABI compatibility.

The builder accepts repeated explicit manifests, so different versions of the
same role can coexist after their identities have been registered in the existing
catalog. Firmware version is not the ELF format header version. Nothing imports
or overwrites the canonical readiness registry implicitly.

```sh
uc-library/.venv/bin/python dependency-graph/native_graph.py --out temp/recovery-work/dependency-graph/UNIQUE_NATIVE_INDEX --manifest PATH_TO_FIRST_EXPORT/manifest.json --manifest PATH_TO_SECOND_EXPORT/manifest.json
```

Without `--manifest`, the current client/server export manifests are used. Use a
new output directory; previous indexes and evidence are retained. NATIVE_ACTIVE.json
records database/report hashes. ELF/manifests/provider source hashes are checked
before context is selected. Changed/unregistered native input blocks selection;
it is never silently interpreted as a leaf or an empty research task.

## Typed observations

- `ELF_CALLS`: immediate direct ARM/Thumb calls.
- `ELF_TAIL_BRANCH`: observed branch outside the symbol range, a tail-branch candidate.
- `ELF_MEMORY_ACCESS`: explicit base/index/displacement memory operands; not
  inferred C++ field names, layouts or ownership.
- `ELF_LITERAL_CELL`: PC-relative literal pool location/value.
- `ELF_ADDRESS_CANDIDATE`: literal value falling in mapped ELF memory. This may
  still be a scalar; it is not a proven data-pointer declaration.
- `ELF_TABLE_FUNCTION` / `ELF_POINTER_CANDIDATE`: data words equal to exact
  function addresses. Vtable names identify table candidates; runtime virtual
  dispatch and generic pointer-candidate semantics remain unproved.
- `ELF_UNRESOLVED`: observed indirect dispatch/decode gaps.

Section offsets/ranges and SHA-256 are checked against original ELF bytes.
ARM mapping symbols distinguish code and literal pools. NOBITS has no file-byte
hash. Pseudocode is bound but explicitly unvalidated; its declarations and even
conditions are not trusted. Relocations, general register value-flow, jump-table
resolution and complete runtime dispatch are not claimed by this first index.

Packets contain full target instruction listings, exact source ELF paths and
file offsets, available pseudocode, one-hop typed relationships and bounded raw
data/table previews. Preview truncation and missing interpretation are explicit.
Neighbor function bodies require a reasoned `expand --query native_body` request.
Native seeds are exact `native:...` IDs from the parent packet. `callers`,
`callees` and `references` use their direction/type semantics. No recursive
transitive bundle is automatically handed to the agent.

## External implementations

`providers` pins library identity, repository root and commit.
`symbol_resolution` records each original native identity's strategy:

| Field | Meaning |
| --- | --- |
| strategy=`reconstruct` | App-specific work; original declaration uncertainty is separate |
| strategy=`external_source` | Bind to the named provider; do not reconstruct its implementation from firmware |
| binding_status=`unmatched` | No source binding established |
| `candidate` | Candidate source API needs review |
| `verified` | Pinned source/encoded-interface evidence, within recorded scope |
| `adapter_required` | Explicit app-side adaptation remains |

Core uses the existing CCL 5.0.0 source-map at commit
`e8cbdea4a4a20e15111f5a690798a259c0374b31`. Core instructions/pseudocode are not
decoded into the packet. Provider paths, hashes, declarations and exact validated
definition extents point to real upstream source. Original return/layout/behavior,
ARM ABI and hardware flags remain false. The marker is not readiness.

The tables support other providers; none are automatically classified from a
friendly name or namespace guess. The current populated external provider is CCL.

## Separate projection generations

Native nodes are not `Artifact` nodes. Source refresh counts only source-to-source
edges; it preserves the native projection. `NativeGeneration` has its own ready/
digest guard. Native publication checks exact SQLite node/edge counts before
making the projection available. `NATIVE_SOURCE_CANDIDATE` is a name-only bridge.
No production readiness schema is changed.

Source refresh still runs automatically before the next batch after C++ edits.
Importing a new ELF/export set is an explicit operator action. Native publication
uses `native_publish.py` in the existing runner Docker image; no host dependencies
were installed. The builder reuses project-local Capstone/pyelftools.

Validation evidence: `evidence/recovery/2026-10-31/dependency-graph/native-index-01/`.
Real reconstruction outcome: `../evidence/recovery/2026-10-31/dependency-graph/live-trial-02/`.
