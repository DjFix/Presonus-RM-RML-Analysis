# large02_w08 source-port replay

The driver exercises the original-named partial classes with pinned real CCL
5.0.0 providers. The oracle runs the exact original ARM application bodies in
Unicorn. Core bodies are never executed or recovered. Native provider calls are
explicit deterministic stubs; complete traces and every original byte range
are retained in fixtures.json. Real host providers independently execute
observer lists, controls, parameters, component dispatch, clocks, attributes,
bitmap lookup, serialization, buffers, typed message provenance and client routes.
The test network boundary only captures outgoing events and never opens a device
or network connection.

The domain includes five setter null/same/replace transitions; separate C1/C2
ranges for each class; D0/D1/D2 with empty/owned-resource cleanup and actual
outliving delete observations; connected/disconnected meter normalization;
three optional controller bindings, missing images and signed bar widths;
parameter messages0..4 at tags0/7/8/15; timer active/inactive state; and stores
and idle expiry with null and non-null client dispatch. Bitmap lookup is real,
but non-empty bitmap loading is not exercised. Native constructor base calls
are stubs; host base constructor behavior is source-provided, not proved equal.
No exception-unwind, reentrancy, allocation-failure, hardware or ARM ABI claim.
The scale pointer's original declared type remains unresolved: this portable
model deliberately uses an owned actual Core::Interpolator, and only conditional
virtual destruction is established by native target instructions.

Invoke replay.py with the canonical built executable and the exact sealed
fixtures.json argument. checks.py builds fresh scratch each run, regenerates
native observations independently, compares fixture bytes, and verifies19
compiled ELF symbol names. Root owns canonical build, CTest and readiness gates.
