# routeInputsToNet portable reconstruction

The original RM 13731 symbol routes a synchronous change notification through
`line/ch1`, `line/ch2`, … parameter tag `0x130`. It does not set parameter values.
Native `+0x1d8` is interpreted as a signed 32-bit count and reread after each
iteration. The portable class reuses `hardwareMicLineInputs` and borrows
`routeInputParameters`; callers keep the CCL tree alive throughout notifications.
All preexisting class APIs/state remain present. The real pinned CCL
`Component::findChild`, `getParameterByTag`, `Parameter::changed` and `CString32`
implementations are used. No Core firmware function is reconstructed or executed.

`oracle.py` checks the full ELF hash, .text section mapping and every original
symbol byte before executing its ARM instructions in Unicorn. Its external
boundaries independently model the pinned CCL source: empty CString32,
`ch%d` formatting, exact child-name lookup, tag lookup and synchronous
feedback/observer notification. The native parameter boundary asserts tag 304.
Only application ARM instructions execute; virtual slot 0x14 is modeled as
CCL `findChild`, an intentional source-port provider correspondence rather than
proof of original provider implementation or vtable compatibility.
The oracle re-reads the actual emulated native count; mutations write its memory
from the modeled observer boundary. `count_writes` are those explicit provider
boundary writes, not an assertion of native app store instructions. Original
application stores to this count are watched separately and absent in this domain.
Stack temporaries and return register contents are excluded from comparison.

The compiled driver uses real CCL child trees and parameters with decoy tag
0x131; test subclasses observe lookups by delegating directly to the real provider.
Real observers mutate the portable count. Ordered lookup/feedback/observer
traces and final count are compared to independent original ARM observations.
Both target and decoy parameter values must remain unchanged. Twenty-three cases
cover absent trees/children, sparse channels, one/two-digit names, negative/zero
and positive signed bounds, INT_MIN, and INT_MAX terminated by first callback
mutation, plus grow/shrink/equal/negative callback updates. Two portable-only
binding guards check missing root and missing parameter; native null-parameter
execution is excluded, since original changed() is called without a guard.
Zero/negative bounds require no borrowed root. Missing roots for positive counts
and missing tag0x130 are explicit source-port logic errors, never silent skips.

Void return, borrowed state, full original class declarations, fields, inheritance,
ownership, layout and ARM ABI remain unproved. This is bounded portable behavior
with source-based CCL boundaries, not hardware validation, original Core binary
behavior, constructor recovery, or whole-object interoperability. Root supplies
production partition registration, canonical CTest, full Linux validation and
readiness admission. No readiness fragment or global ledger changes are included.

Run `uc-library/.venv/bin/python uc-library/candidates/large02-avb-route01/checks.py`
with `format`, `oracle`, `compile`, `symbols`, or `replay`. Each creates unique
scratch beneath `temp/recovery-work/large02-avb-route01`. CMake registration is
provided locally; canonical CTest must call replay.py with the built executable
and explicit fixtures.json. Keep fixture generation independent of the driver.
