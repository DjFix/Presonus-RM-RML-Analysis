# GroupsPageComponent bounded portable reconstruction

Five exact original member identities compile in `Presonus::Surface`. This is
an explicit source port, with independent `presonus::surface` state and required
application dependency interfaces. It does not establish original object layout,
inheritance, return declarations, ARM ABI or hardware interoperability.

`oracle.py` verifies each full ELF range using section 12's actual file mapping,
loads original PT_LOAD bytes, and executes the target ARM instructions with
Unicorn. Calls between the three offset methods execute original instructions.
Calls to refreshList, doselect and observeGroup are captured boundary hooks,
not reconstructed functions. The parameter virtual setter is captured as a
boundary; portable production uses actual pinned CCL Parameter::setIntValue.
CCL ConstVector supplies production containers and error cells. No Core binary
implementation is recovered. Original NOBITS pointer error cells initialize to
null. The test's NumericParam subclass captures setValue before calling its real
upstream implementation; this proves argument/order binding, not original setter
implementation equivalence.

`check.py replay --executable PATH --fixtures PATH` sends every fixture input to
an explicitly supplied built C++ executable, then compares result, final offset,
selection, observed pointer, and ordered call traces directly with the original
ARM observations. Native object writes are additionally retained in fixtures.
Callbacks are nonmutating in this bounded domain. Arrays/pointers are valid;
invalid-pointer crashes and callback-driven mutation are excluded. Count extremes
exercise arithmetic-only methods without indexing those arrays.

Original setListOffset compares the clamped request before rounding it to even.
Consequently an odd request can trigger refreshList while storing the same even
offset. Addition/subtraction use explicit 32-bit wrapping to match observed ARM
arithmetic without signed C++ overflow.

Root retains shared build integration, Linux CTest and guarded readiness admission.
All five targets remain declaration pending. Dependency hooks remain explicit
unresolved application boundaries and are never default no-op providers.
