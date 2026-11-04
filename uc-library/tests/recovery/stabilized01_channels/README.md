# Initialized channel selection source port

Original namespace/mangled identities are retained for five methods and nine
original ELF occurrences. Return pointer spelling, ChannelType enum declaration,
private fields, original inheritance/ownership/layout, ARM ABI and hardware
interoperability remain unresolved. Source constructors are independent setup,
not recovered original lifecycle methods.

`MixerClientComponentBase` composes a real CCL5 Component tree. The source setup
borrows the tree and cached channel; callers retain their lifetime and externally
invalidate selection by constructing a new initialized source context. Existing
PortableMixerState convenience behavior is retained. CCL Component owns actual
children added to it; the source model neither adds nor deletes borrowed groups.
SLChannel borrows a real CCL Parameter. SLChannelBase derives from actual pinned
CCL Component for source composition; its selected source type ID 0x534c4342 and
core_cast replace original compiler RTTI intentionally. This is source adaptation,
not proof of original RTTI layout. Parameter values use actual CCL NumericParam.

The complete null-cache scan checks groups 0..8 even after finding a selection;
the first positive selection of each later group overwrites the previous cache.
The cache is returned immediately on later calls. Null children, failed casts,
base-null providers, derived-null parameters, negative/zero/NaN/positive/infinite
values, absent/empty groups, multiple positives per group and across groups are
covered. Group lookup tests all switch values 0..10, missing names, negative and
out-of-range types; name classification covers all ten exact names and mismatches.

`oracle.py` loads each SHA-256-bound original ELF's PT_LOAD ranges into Unicorn
2.1.4 and executes the original app instructions. It separately verifies all nine
symbol ranges using ELF section-to-file mapping. Core binary bodies are never
executed or recovered. Native findChild, compiler __dynamic_cast, strcmp, float
greater-than and parameter getValue boundaries are modeled explicitly from the
fixture's valid memory/type/name/float inputs. No original libc/Core/compiler
runtime execution is claimed. The CS18 SLChannelBase and each SLChannel getter
execute their original instructions through synthetic virtual slots. The RM base
null provider is modeled because that original body is outside the sealed target
set; the two original RM assigned ranges and all assigned other ranges execute
independently. No cross-version execution edges are used.

The native parameter hook returns raw float register bits; the host uses actual
CCL NumericParam::getValue. Float comparison is IEEE ordered greater-than; NaN
is not selected. Native synthetic arrays assume stable valid storage and compiler
cast type relationships; host uses actual CCL Component vectors and core_cast.
Native traces retain lookup/cast/value/strcmp events and cache writes; host replay
compares normalized returned identities, value-read counts and persistent cache
behavior. Test-only null child slots are inserted into actual protected CCL Vector
and removed before normal Component destruction. No production callback, no-op
provider or pointer reinterpretation substitutes for selection logic.

Per-function exclusions: base getter: original C++ return and lifecycle unresolved;
derived getter: pointer ownership/private offset declaration unresolved; group
lookup: original Core virtual provider behavior excluded in favor of pinned CCL
findChild; group classification: original libc strcmp execution excluded; selected
channel: original compiler RTTI/Core parameter implementation, concurrent mutation,
invalid memory, unrelated bootstrap/vtable paths and hardware excluded. Native
observations and source-port provider tests are distinct proof scopes. Local
acceptance is not readiness admission or global Linux integration.
