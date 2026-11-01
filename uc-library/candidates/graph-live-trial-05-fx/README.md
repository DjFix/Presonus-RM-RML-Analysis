# FXComponent bounded source port

Five original RM/RML 13731 identities are implemented in their original class
scope. `presonus::mixer_fx::State` and `AppBoundary` are independent portable
adaptations, not recovered original fields, inheritance or provider interfaces.
Core parameters and parameter membership use the actual pinned CCL source.

`native.py` verifies the complete ELF hash, original symbol ranges, ELF section
mapping, bytes and sealed packet manifests before executing each target in ARM
Unicorn. External calls are explicit boundary stubs: no Core firmware body is
executed. The getValue/setValue slots (0x44/0x58) are interpreted as parameter
operations, corroborated by the Root-supplied named AliasParam table identities; this does not prove an original
layout or virtual table ABI. Original helper bodies, controller internals and
complete application integration are excluded from this bounded test domain.

The fixture records original target writes, normalized app/parameter traces,
provider access traces and register results. The C++ executable uses actual CCL
Component and NumericParam code. A test subclass records virtual calls and then
calls actual NumericParam getValue/setValue. Component membership executes actual
CCL countParameters/getParameterAt. Native count/getAt stubs use supplied finite
lists. Their call sequence is retained but not claimed as a native Core replay.
Unsigned-to-float is an explicit IEEE binary32 conversion boundary stub, not a
recovered libgcc implementation. Native writes to dirty/pending flags and their
state as observed by callbacks are compared to C++ state. Parameter setter inputs
and edit flags are compared; complete provider-internal side effects are outside
this domain.

All five original return declarations remain unresolved. Chosen portable returns
are void for setFxDirty, ParamValue for mapValues and bool for the others. Encoded
parameter/scope identities compile exactly; that fact does not establish original
returns, member/static/virtual declarations, class layout, ARM ABI or hardware
interoperability. AppBoundary deliberately requires providers for unrecovered
app-specific dependencies. It is not a production Core provider or a claim those
dependencies are implemented here.

Replay accepts `--executable` and `--fixtures` explicitly so canonical CTest can
compare the exact native observations against its own built executable. Root
owns CMake integration, full Linux checks, readiness schema/admission and trackers.
