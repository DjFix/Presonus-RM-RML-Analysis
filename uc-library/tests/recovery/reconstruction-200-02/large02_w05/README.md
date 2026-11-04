# AVB state/lifecycle portable source proposals

The fixtures originate in exact original RM 13731 ARM instructions executed
with Unicorn. Core firmware instructions are never executed: native Core calls
are explicit observed boundaries. The portable executable uses pinned CCL 5.0.0
Component/Parameter implementations. Real child destruction and real deleting
destructor deallocation are observed through outliving state. Original vtable
writes stay native-only evidence and are never read from destroyed C++ objects.

Replay interface: `replay.py --executable DRIVER --fixtures fixtures.json`.
Root integrates the exact proposal bytes, adds the single CPP to the common
OBJECT partition, includes this test directory, then replays all global gates.
Local checks compile the canonical existing AvbComponent.cpp against this overlay
and copy mutable Core/allocator link inputs into fresh scratch with SHA-256
provenance. No old precompiled app object is linked across the new declaration.

Original return declarations for ordinary methods, original class layout and
ARM interoperability are unproved. Inheritance and storage here are intentional
source-port choices. Native unwind/throw paths and actual AVB hardware are outside
the replay domain. Resource and ListenerServices are explicit external AVB
boundaries, with test implementations capturing calls.

The eighth dispatched identity, AvbComponent::paramChanged(Parameter*, int),
remains blocked. Its five native observations are retained as `native_only_cases`
and are not counted as portable replay successes. No production override is
provided. Root explicitly retained this pending workload and will select the
actual onCascadeLinkStateChanged provider closure before reconstructing it.
The seven completed originals cover 26 portable replay cases.
