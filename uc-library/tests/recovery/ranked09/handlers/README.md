# Handler source-port replay

Five CS18AI 13840 exact identities, individually verified source ELF ranges.
Original ARM instructions execute under Unicorn without call stubs. Synthetic
valid object/vector/row memories and mutable error cells define the bounded domain;
these are test inputs, not recovered layouts. NOBITS begins zero in emulation.
Fixtures retain executed PCs, data-cell reads, storage/count writes and outputs.
Pointer tokens are compared by identity, never dereferenced as handler/observer
objects. C++ uses actual upstream Core Vector and ListViewModel/ListViewItem.

Null/duplicate/absent entries, negative/large indices, first/middle/last removal,
zero/nonzero error cells, selected/no-selected and userData matching are replayed.
No original ordinary return declarations, layout, inheritance, ownership,
initialization/lifecycle, cross-version semantics, ARM ABI or hardware credit.
The added setup APIs and constructors are independent portability glue. Existing
source-port page declarations are extended, not duplicated.

Root integrates AssignmentHandlerTable.cpp, PageObservers.cpp and
NetworkListSelection.cpp once each in CS18 OBJECT partition (selected native
identities client-only; no broader exclusivity inference). Public headers are
AssignmentHandlerTable.hpp, sl_mixer_encoder.hpp, NetworkSetupComponent.hpp.
Link the driver to the canonical CS18 facade and actual CCL; retain facade target
name presonus_cs18_components in the proposed local CMake file.
Canonical CTest must execute replay.py against the canonical built executable
and these hash-bound fixtures. Local checks build only assigned scratch.
