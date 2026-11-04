# SLMixerHandler initialized lifecycle and actual color providers

This is a portable C++ source port, with no original layout, original ordinary
return declaration, raw vptr-reset, ARM ABI, or hardware equivalence claim.
`SLMixerHandler` retains its explicitly borrowed compatibility constructor.
The distinct protected `OwnedLifecycle` setup is independent source glue:
EQ/Geq pages are borrowed observers, only the supplied color converter transfers
ownership, and the actual CCL ParamList/vector members own their normal storage.
Copying this independent owned composition is forbidden. Native +0x20 is not an
owned deleting dependency. This work claims no original constructor recovery.

Normal cleanup detaches actual EQ/Geq observers, calls actual
`setDigitalParams(nullptr,nullptr)`, deletes the converter, then destroys boolean
vectors, component-pointer vector storage, actual DelayTimer and actual CCL
ParamList/owned parameters and storage. Component pointers are borrowed, not
deleted by a Vector. The legacy compatibility constructor is excluded from
original lifecycle credit and never adopts its fixture-assigned page pointers.

`MixerColorConverter` is in its original global C++ scope, with the evidenced
`Presonus::IColorConverter` base. It calls actual ColorMapping providers through
an intentional source adaptation of the original thin MappingTable wrappers;
it does not use the independent legacy MappingTable integer callbacks. The
converter index table is distinct from ColorMapping enum order. Index0 and
out-of-range indices return transparent black (`default` name misses the
ColorMapping palette); `off` returns opaque black. Ordinary return spellings,
including `Core::Color`, remain source choices where no original declaration
independently establishes them.

The oracle checks each exact ELF range, section mapping and byte hash, including
both distinct base/derived D1 ranges. It executes actual app destructor/helper,
MappingTable wrapper and existing ColorMapping native instructions. It captures
receiver writes, observer-list shifts, provider calls and original D0 calls into
operator delete. Its explicit allocator boundary unmaps tracked native pages and
checks they cannot be read. Native Core bodies are excluded: CCL vector,
parameter-observer and ParamList cleanup are explicit source-provider boundary
adapters. Their bounded operations are compared against the actual CCL C++
providers, including real frees, not presented as original Core binary behavior.
libc strcmp/string copying are explicit string boundaries; compiler floating
support is reused from the existing original palette oracle. No app helper
returns fixture-supplied results. Expected results never use reconstructed C++.

The host driver calls the exact compiled SLMixerHandler D0/D1/D2 symbols directly.
Its forwarding wraps invoke real production helpers and record ordering; global
operator delete observations forward to real `free`. It exercises registration
between two retained actual observers, both digital pointers (including shared
parameter identity), null/non-null converter, empty/populated Core containers,
ParamList-owned parameter and member vector storage, plus post-destruction real
parameter notifications. Independent native fixtures cover 192 initialized
lifecycle cases, 4 base/derived color destruction variants, 27 string inputs,
23 index values, and 85 RGBA inputs (331 total).

Native D1 bodies both write the independently observed IColorConverter base
vptr 0x1a00b0. The optimized Linux host D1 bodies are `endbr64; ret`: the host
compiler removes unobservable ended-lifetime vptr writes. Native writes are
preserved in fixtures and host disassembly is preserved in the proof; raw vptr
write equivalence is deliberately excluded. Matching mangling/free counts is
not evidence of those writes, binary layout or ABI compatibility. Exceptional
unwinding, allocation failures, invalid lifetimes and hardware are excluded.

Root integrates three production CPPs exactly once using measured role ownership,
adds this CMake subdirectory and retains global tests/readiness admission. Local
checks use immutable, hash-checked provider snapshots; they recompile all affected
application units and preserve exact commands, dependency hashes and outcomes.
Seven existing affected fixture drivers are independently rebuilt/replayed.
The nine exact packet handoffs are indexed in
`uc-library/candidates/large02-lifecycle-fix01/HANDOFF_INDEX.json`.
