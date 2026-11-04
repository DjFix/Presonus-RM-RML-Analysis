Bounded portable source port of Presonus::Panel::PresetComponent::isSlotEmpty.

The native oracle executes only the exact hash-verified 72-byte application body.
It intercepts getFileNameForSlot with observations from the actual existing app
implementation/cache and fileExists with observations from pinned CCL's actual
POSIX provider. It never executes Core firmware. Fixtures are independent of the
new isSlotEmpty body. Seven filesystem states cover missing files, regular files,
directories (CCL fopen semantics), valid/dangling links, whitespace trimming and
the cache empty marker. Slot values 0–3 are bounded to a four-entry cache.
An eighth native-only empty-filename case covers the early return and lack of a
provider call; current cache output is nonempty, so this branch is not claimed
as exercised through that portable model. Native stack writes and call sequences
are recorded. The C++ replay verifies real service/cache flow and return values.

Original full declaration, return spelling, class layout/ownership and ARM ABI
remain unresolved. The bool return is an intentional portable source contract.
Existing services, cache implementation and recall boundary are preserved.
Test services throw if unrelated interfaces are unexpectedly invoked; they do
not replace filename generation or file existence. No hardware was involved.

Root should include this test directory after shared integration. The production
CPP already belongs to the RM object partition, so no new production TU is needed.
Canonical CTest invokes replay.py against its actual built target and the explicit
immutable fixtures.json. Each oracle/replay uses a fresh project-local scratch
folder, preserving all sealed inputs. Worker linkage uses immutable copied app,
Core and allocator archives; canonical integration must use current role targets.
