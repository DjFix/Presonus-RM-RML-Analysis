Runtime globals bounded source port

The five exact RM 13731 identities are represented with original namespace/C
linkage names and explicit independent `presonus::dsp::RuntimeMemory` guest-word
bindings. They consume the same ARM32 global addresses in one thread-local
binding. This is a portable guest-address-space interface, not host pointer or
original mixer/audio/link class declarations. It deliberately fails on missing
binding; callers supply real memory adapters appropriate to their environment.
No original ordinary return declaration, class layout, ARM ABI, live application
state, hardware operation or cross-version equivalence is established.

The oracle verifies the complete ELF SHA-256 and each actual section-mapped
symbol range, then runs original ARM instructions in Unicorn 2.1.4 with
explicitly initialized memory. Global symbols are SHT_NOBITS; supplied nonzero
state is synthetic and is not claimed as recovered live state. 81 fixtures cover
null/non-null gLinkPtr, state words 0/1/all-ones/high-bit, readiness magic and
adjacent mismatches, shutdown initial words 0/1/all-ones, and AudioHAL 32-bit
addition wraparound. Ordered relevant reads and writes are compared, including
null guards and repeated reads after rebinding between fixtures. Native stack
frame reads/writes are outside the portable semantic domain. shutdownDSP has no
observed consumed parameter or defined return; the portable declaration uses
void and the native R0 is excluded. It only changes supplied offline guest
memory; no real DSP process is executed. There are no external call boundaries
or Core provider dependencies in these ranges.

Local checks are `uc-library/.venv/bin/python
uc-library/candidates/ranked09-runtime/checks.py MODE`, with MODE format,
compile, symbols, oracle or replay. Root must integrate RuntimeGlobals.cpp once
in the RM OBJECT partition, expose RuntimeGlobals.hpp, add the test directory,
and run replay against its canonical executable and this hash-bound fixture.
All original declarations remain compiled-pending.
