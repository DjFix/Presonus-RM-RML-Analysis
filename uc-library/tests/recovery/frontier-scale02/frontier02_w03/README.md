This test replays the original RM 13731 SLReverbController(int) constructor range
at 0xbf358, size 260 (including literal cells), and executes its actual Controller C2 and Biquad C1 providers, comparing every
initialized object byte except native vtable words. Five input IDs cover
zero, one, negative one and both signed int endpoints; distinct sentinel fills
make untouched memory and target writes distinguishable.

Production uses the real Controller(id,nullptr) constructor and real
DSP::BiquadCalc<double,false> constructor. SLReverbController is intentionally
abstract because the unrelated setValue virtual remains unresolved. The Probe
fixture supplies an exception boundary and verifies that construction never
calls it. Borrowed-state fixtures verify old getValue/setReverbValue/setDirty
storage still operates on the caller's state.

The owned valueCount callback remains unbound: the native constructor initializes
57 entries but does not establish provider semantics. Operations using that
callback require an actual caller-supplied binding; the regression uses an
explicit test-only count boundary after construction.

The owned source model is zero-filled; original untouched bytes, C++ ownership,
allocation exceptions, full virtual declarations, object layout, ARM ABI,
hardware, and the existing app-DSP dependency callbacks are outside the claim.
Native pointer/table addresses are recorded, never installed as host pointers.
The native execution records exact ARM arguments and all target/provider stores;
it intercepts no calls. The C++ fixture projects named Controller source slots
into the native observation offsets and compares initialized Biquad state read
from the real provider. This fixture projection does not assert host layout.

Root should add this directory to the canonical tests. Its CTest command uses
the canonical executable and explicit fixtures.json; checks.py builds in new
assigned scratch using immutable archive copies and never changes fixtures.
