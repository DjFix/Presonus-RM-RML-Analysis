# large02_w07 bounded reconstruction replay

The fixtures execute exact original ARM application instructions for the 24
sealed targets and required bounded helper closure. The primary workload remains
24; helper coverage earns no additional target/readiness credit. `oracle.py`
verifies the exact ELF and helper ranges and permits application execution only
inside those ranges. Known business helpers updateParams, doselect, updateFilter
and existing updateSelection execute their actual original bodies, rather than
fixture callbacks. Core/libc/floating and unresolved mixer virtual providers are
explicit boundary models. No Core firmware code executes.

Production `BorrowedMixerPageAccess` registers explicit actual
MixerClientComponentBase identities with borrowed typed CCL trees, channel
containers, slave/root/selected-channel views and selection output state. It
rejects unregistered identities, duplicate identities and missing field bindings;
explicitly bound null providers remain distinct from missing bindings. These
views are intentional independent source-port composition, not recovered mixer
fields, inheritance, vtable layout or proof of original virtual-call semantics.
Application callers must populate them from their real model during integration.

Mapping calls use the actual supplied IMappingController interface:
getMainScreenParamByTag(25) for launchEdit and getParamByTag for selection radios.
The helper uses actual CCL AliasParam::setOriginal. Native RTTI casts are adapted
to real CCL AliasParam::cast because the pinned provider archive omits native RTTI;
this is a documented source-port adaptation, not original ABI fidelity.
Page visibility uses actual immutable PageComponent.cpp. Known refresh and
selection helpers no longer delegate to the old callbacks. The old Groups
constructor signature remains for source compatibility; callback-only callers
must bind actual page/access/required parameters instead.

Fixtures retain native external calls and object writes separately from
normalized portable results. Both O0 and O3+DNDEBUG drivers use actual CCL
providers and actual MixerState.cpp. They validate alias rows, filter/radio
selection effects, observer changes, list state and destructor deallocation.
An outliving delete observer records real host free; native D0 deallocation
unmaps modeled object storage. Destroyed host objects/vptrs are never inspected.
Exception unwinding, original nonempty cleanup and ARM interoperability remain
outside the validated scope.

Run `uc-library/.venv/bin/python uc-library/candidates/large02_w07/checks.py all`
from the repository root. Each run uses fresh owned scratch, checks format,
compiles both modes, checks all exact primary names, replays the fixtures,
checks production-adapter rejection contracts and reproduces native fixtures.
The proposed CMake entrypoint invokes this exact replay with a canonical built
driver and explicit canonical fixtures. Root integrates each production unit
once and chooses LARGE02_W07_LIBRARY_TARGET. Canonical CTest, role/install,
current-source, guarded SQLite and readiness decisions remain Root-owned.
