# LinkableComponent bounded source port

Five original RM 13731 identities are implemented in their original class scope.
The independent `Presonus::linkable_port::State` is explicit portable storage,
not an original class layout. The required `Boundary` supplies app-specific
query, virtual remove/set and master-link behavior. It has no default provider.
No Core type or implementation is fabricated, and no Core instructions execute
in the oracle. All original return declarations and inheritance remain unresolved;
the chosen void/bool source contract does not establish them.

The replay covers 96 cases per target (480 independent original ARM executions).
It compares all four nodes' partner/slave/enabled state and callback-time snapshots
plus callback receiver/arguments/order. Native raw writes and r0 observations are
retained separately. Only isLinked's Boolean-valued result is compared; other r0
values are not assertions about original returns. Inputs include same/different
partners, self-partners, null partners, dirty slave bytes, enable/disable, empty
and populated child arrays, null children, failed/successful interface queries,
duplicated children and acyclic nested recursion. External callbacks are controlled
stubs returning a fixed register value, except query's pointer-or-null result.
Callback mutation/reentrancy, cyclic children, concurrency, invalid memory, full
master-link behavior, CCL integration and hardware are outside this proof.

The expansion confirms master-link invokes app-specific parameter/alternate-memory
work and source-provided Core APIs. That dependency is not reconstructed here;
setLink's dispatch boundary is the tested scope.

Run checks from the repository root:

```
uc-library/.venv/bin/python uc-library/candidates/graph-live-trial-04-linkable/check.py format
uc-library/.venv/bin/python uc-library/candidates/graph-live-trial-04-linkable/check.py compile
uc-library/.venv/bin/python uc-library/candidates/graph-live-trial-04-linkable/check.py symbols
uc-library/.venv/bin/python uc-library/candidates/graph-live-trial-04-linkable/check.py replay
```

For canonical integration, pass the built test executable as the last argument to
`check.py replay`; it compares the same explicit fixture. Working directory must
be repository root. Root owns production CMake, registry fragments, merger and
full Linux integration. These handoffs are local evidence, not admission.
