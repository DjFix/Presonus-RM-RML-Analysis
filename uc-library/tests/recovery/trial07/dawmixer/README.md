# DAW mixer regression replay

`fixtures.json` contains observations from the original CS18AI surface 13840 ARM
instructions. `replay.py --executable PATH --fixtures PATH` sends the bounded
inputs to an explicitly selected C++ executable and compares state, four mix
parameter identities, automation/mapping values, parameter set/edit events and
ordered application boundary calls. The runtime requires only these maintained
tests and fixtures; no operational readiness/proof JSON is consumed.

`native_oracle.py` independently regenerates fixtures from the SHA-256-identified
ELF. Exact target symbol names, sizes, sections and file ranges are checked
against the separately selected native context before execution. Execution
outside the ten target ranges and explicitly modelled boundary hooks fails.
Every case retains the executed target PCs, native writes and raw boundary calls.
Core methods are never executed or reconstructed from firmware: lookup/value/
enabled/set operations are synthetic native boundaries, compared with actual
pinned CCL Component, ParamList and NumericParam implementations in the C++ test.
Soft-float conversion/addition helpers and strcmp are also explicit boundary
models. Remaining DAW component/folder/group, mapping-table and assignment
operations are application boundary models, not recovered implementations.

The 24 integer input columns are: method (1..10), selected mix, client present,
controller present, group selector (0 other / 1 main / 2 input / 3 output), channel
present, folder present, used count, allocated slot count, nonnull slots, channel
type (0 null / 1 AudioOutput / 2 other), changed parameter tag, flex-strip flag,
modifier bitmask, previous shift byte, previous meters byte, requested meters,
source parameters present, automation parameter presence mask, IEEE float bits
for channel automation, parameter enabled, focus equals changed channel,
main-screen parameter present, and nonzero initial target identities.

The output numeric columns are the shift and meters bytes, four MixTargets
identities (only for method 3), four automation float bit patterns and the
main-screen parameter float bits. Semicolon-separated events follow in original
order. Null pointers map to identity zero. Missing automation parameters retain
the initial fixture observation 0.25; their absence is also in the input mask.

Domains include supported send/cue/main mix boundaries, nulls, sparse targets,
used-vs-allocated slot bounds, AudioOutput's preserved mute target, exact channel
and mapping tag dispatch, modifier bit 2 transitions, show-meter changes,
controller/main-screen parameter absence, and finite automation half-step
rounding with sparse destination lists. Float NaN/infinity/out-of-int-range,
invalid native object/vtable storage, nonzero global vector error sentinel,
concurrent mutation, physical hardware and original return/layout/ARM ABI are
excluded. Methods that dereference a controller or changed parameter retain
those original nonnull preconditions.

The existing Presonus::IMappingController interface is reused for real app
controller calls. The C++ test overrides its boundary methods and uses real
CCL parameter storage. Production DAW boundary operations are required through
an independent interface; they have no silently successful default provider.
Original unencoded return declarations are pending; production void returns,
MixTargets member spellings and all new storage are intentional source-port
choices. Original ARM parameter vtable slots are used only in the oracle;
production calls use the current CCL declarations and compiler-selected vtable.
