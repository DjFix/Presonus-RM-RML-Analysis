Independent oracle: `oracle.py` loads the SHA-256-bound CS18AI surface 13840 ELF
and executes exact original ARM instructions in Unicorn. Calls to the actual
TempoMap search and compiler soft-float routines execute original instructions;
no call-replacement hooks or Core methods execute. The allowlist rejects other
instruction ranges. Captured fixtures retain original full ranges and section
file offsets, executed symbols, memory writes and call addresses.

The 557 cases cover pointer offsets, the transport string, D1 base-vptr write,
map boundaries, seconds-to-PPQ and clock/musical delta event generation.
`replay.py` compares a supplied canonical built executable with those fixtures.
Production and testing both use the actual existing UC::TimeCodeEvent fields.
The driver explicitly projects those portable fields into native semantic byte
offsets; it never treats host object layout as original ARM layout. Full native
112-byte observations include 24 trailing sentinel bytes outside the portable
event payload; these trailing bytes are projected as unchanged sentinels.

The source model is portable. Original returns, full interfaces, layouts,
inheritance and ARM ABI are not established. Getter pointer/const returns are
provisional; mutable mode returns actual source-state time objects. Borrowed
mode returns observed byte addresses and requires readable borrowed storage.
The virtual destructor is a partial interface: only selected D1 behavior is
observed; no D0 deallocation claim is made. The production destructor explicitly resets an ELF-specific opaque dispatch
identity token in independent borrowed `presonus::dawtime::DispatchState`, which
must outlive its C++ object. The replay observes that real destructor effect and
all 508 unchanged sentinel bytes in the still-live state. It never reads host
vptr bytes after C++ lifetime ends or claims that the token is a host address.
The constructor is an independent borrowing adapter, not a recovered original
constructor. This explicit source-port adaptation preserves the bounded native
D1 identity-store observation without inventing layout or deallocation. NaN/Inf/zero tempo divisor, malformed
map storage/counts, unsorted records, arbitrary original virtual dispatch and
hardware interoperability remain outside this replay domain. Original native
symbol identity is separate from source-level declaration fidelity.

Root integration: keep DAWTimeMaps.cpp common, add the new production CPP once
to the CS18 partition after role ownership review, expose the owned partial
header, and bind the CTest above to actual facade target name. Worker does not
modify shared CMake, partitions, registry or readiness. All check invocations
allocate fresh scratch and compare sealed input hashes before/after.

Optimized local acceptance compiles with `-O3 -DNDEBUG`; all 557 original
fixtures remain unchanged. Prior sources/producers/manifests/fixtures are
preserved in `evidence/recovery/2026-11-03/dependency-graph/reconstruction-200-01/large01_w05-before-optimized-fix01/` with a hash manifest.
