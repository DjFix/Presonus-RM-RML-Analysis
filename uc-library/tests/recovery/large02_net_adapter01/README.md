# AdapterHandler owning initialization

This source port adds `Presonus::UC::AdapterHandler::AdapterHandler()` with
private owned state and the actual existing `CclAdapterServices` provider. It
retains the tagged borrowed constructor as an independent source API. The
independent `presonus::uc::sourceAdapterSingleton()` helper uses pinned CCL
`StaticSingleton`, without assigning a borrowed object to a singleton pointer.

The independent ARM oracle executes all four original C1/C2 ranges separately
(two firmware versions). Native C1/C2 are distinct ranges; the host compiler emits
both exact original names at one shared entry address. Four different receiver
prefills expose untouched bytes and all explicit stores. Two original calls to
Core CStringBuffer constructors are intercepted at a pinned-source boundary:
`CStringBuffer(nullptr)` writes just its first byte. Core firmware and target
libc are never executed. The host uses real pinned CCL strings and IPAddress
values; all ten initialized native addresses have 36-byte size, family 2 and a
zero payload. The list starts empty, both strings are empty, and known control
flags/counter are zero. No constructor invokes networking; abort-only wrappers
for network/hostname/resolver calls enforce this at host runtime.

The owning interval adaptation is separate from the unchanged borrowed
`AdapterHandlerState` default of 1000. See the bound native process mapping in
the local proof. Original process instructions were additionally executed for the
first 101 calls from every C1/C2/ELF initialized receiver, independently showing
counter 101 with no provider calls; host execution matches under network abort
boundaries. The independent source accessor `sourcePortState()` exposes
source storage to composition and testing; it is not an original ELF interface.

The driver executes normal complete construction and base-subobject construction
separately, tests real freeing of owned source allocations, preserves an
externally supplied state after borrowed-facade teardown, and checks repeated
access through real CCL StaticSingleton. Host destruction is a source-port
resource test, not recovery or validation of an original AdapterHandler deleting
destructor. No destructor identity was assigned in these packets.

The original class fields, widths/types beyond observed stores, private layout,
inheritance and ARM calling convention are unresolved. Native halfword zero
stores at offsets 0x22, 0x24, 0x2c and 0x2e remain raw observations without invented
member declarations. Uninitialized string tails/padding and raw representation
of the source owning pointer/reference are excluded from host equivalence.
Constructor failure, unwinding, races, networking/device access and hardware
interoperability are excluded. Matching mangling establishes names only.

`checks.py` compiles only the owned production units and this driver in assigned
scratch, linking the current Linux pinned CCL build. Root integrates the lifetime
unit once into the common production partition and the test CMake subdirectory;
CTest invokes `replay.py --executable <canonical target> --fixtures fixtures.json`.
`replay.py` regenerates every original oracle observation before comparing host
outputs. No global readiness or CMake file is modified by the worker.
