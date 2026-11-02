Controller setupProcess portable source port

The original 52-byte ARM body reads the incoming property word at +8, compares
it through the actual __aeabi_fcmpeq helper, and conditionally stores dirty=1
and the unchanged incoming bits at observed receiver offsets +0x1c and +0x24.
The compiler's conditional stores are authoritative; the decompiler export
incorrectly presents the final writes unconditionally.

Production storage extends the existing ControllerSourceState. SetupProperty
remains opaque, as in the existing SLReverbController source port. The borrowed
reference must designate at least 12 readable bytes. This is an explicit native
property-access boundary, not a recovered SetupProperty declaration/layout.
The ordinary original return type, original class layout/inheritance, ARM ABI,
floating environment side effects, and hardware interoperability are unresolved.

The oracle executes original ELF instructions and all actual comparison helper
callees, with no callable stubs. It records exact resulting rate bits, dirty
byte, actual state writes and helper entries, checks unchanged surrounding state
and immutable property storage. The C++ replay compares observable final state.
Test-only abstract-controller implementations never execute for this target.

Fixtures cover finite rates, both zeros, infinities, signaling/quiet NaNs,
subnormals and randomized raw words with initial dirty bytes 0, 1 and 173 plus
random bytes. This bounded replay proves source-port state behavior only.
