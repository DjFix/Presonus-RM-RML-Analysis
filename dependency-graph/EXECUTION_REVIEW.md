# Execution-boundary review

New `mode: reconstruct` requests run `execution_review.validate` through
`reconstruction_contract.validate_request` before contract evaluation. This is
task planning, not readiness or semantic proof. Research still needs its normal
identity, native-body, context and ownership checks.

Use `execution_review.collect(connection, task['targets'])` on the exact database
selected by `NATIVE_ACTIVE.json`, with `sqlite3.Row` as the connection row factory.
Each target must match ELF SHA-256, mangled name, address and size. The collector
returns SHA-256 observation keys for direct calls, tail branches and ARM indirect
control-flow candidates. Name correspondences are not execution edges; indirect
candidates are not inferred virtual-call targets.

Add `execution_boundary_review` to the contract review, containing the verified
database `native_sha256` and an `observations` list covering every collected key
exactly once. Each entry needs `key`, `kind`, `reason` and nonempty hash-bound
`evidence`. Entries of kind `dependency` also need an integer `dependency_index`
into the same review's `dependencies` array. `local_control_flow` is allowed only
for an indirect candidate with supporting evidence; proven call/tail edges cannot
be dismissed this way.

Every evidence reference needs repository-relative `path`, current `sha256`,
nonempty `scope` and typed `kind`: `cpp_declaration`, `cpp_implementation`,
`provider_source`, `native_observation`, `review_record` or
`compiled_symbol_audit`. C++ references must point to actual C++ source. Rehash
the complete review and bind it through the task's `reconstruction_contract`.
Then use ordinary prepare and sealed batch dispatch.

Coverage does not establish provider behavior. Root must review actual native
instructions and source, including computed jumps and virtual-call targets.
The ordinary dependency contract still blocks unresolved providers. Unknown
declarations/state may instead be assigned bounded owned work with an objective
and oracle plan; zero reconstructed inputs does not itself exclude a target.
This check is not automatic transitive provider closure or proof of original
return declarations, layout, ARM ABI or hardware behavior. Preserve all worker,
Linux integration, role, symbol, behavior and guarded registry admission gates.

Historical calls to `reconstruction_contract.evaluate` do not execute this new
prospective coverage check and cannot establish that a new task satisfies it.
