# Mackie panel and MIDI state source port

636 independent ARM instruction observations cover all ten sealed packet targets.
`oracle.py` verifies source ELF SHA-256 and actual symbol section/ranges, then
executes original app code with Unicorn 2.1.4. The actual sendMidiMessage dispatcher
and original non-Core compiler fmul/f2uiz helpers execute as dependencies; only the
abstract MIDI receiver is a stub that captures bytes, length, receiver and port.
Unexpected execution addresses fail. Core firmware never executes.

The fader literal is **0x467fc000 / 16368.0f**. Tests cover normalized finite float
inputs, all nine cache locations, cache hits/misses, int32 tag wrap edges, signed
encoder clamp including INT_MIN, borrowed setter values, ignored MIDI port input,
null sink detachment, D1 non-deallocation and preserved non-dispatch bytes.

`MackieControlModel` keeps existing callback adapters. Before setMidiSink selects
the application interface, the existing callback adapter works unchanged. An
explicit selection uses the borrowed IMidiSink, including null to detach, with
zero outgoing port as the original dispatcher does. The partial IMidiSink virtual
operation is an intentional source-port boundary; its chosen name/declaration is
not an original recovered full interface or original ABI assertion. IFaderPanel
is abstract via its pure destructor; seven unknown native pure virtual slots are
not replaced with fabricated implementations. The existing component uses real
CCL Component and now contains an actual portable model. getModel returns that
member by borrowed pointer; it allocates nothing. The native +136 address is
normalized to member identity rather than reproducing ARM layout.

D1's native vptr reset to 0x1ea978 is checked in original execution. Portable C++
compares the common lifecycle subset: actual destructor call, no deallocation
(operator-delete observation), and unchanged derived payload. It does not assert
vtable byte layout or optimizer-dependent post-lifetime dispatch bytes. D0/D2
emitted by the host compiler are not admitted as original reconstructed targets.

Original unencoded return types, complete class declarations, inheritance,
ownership beyond observed borrowed stores, original static membership and ARM32
ABI/layout remain unresolved. float NaN/infinity/negative/out-of-range inputs are
outside the behavioral domain. Saturating host conversion outside that domain is
an explicit portable adaptation, not validated original behavior. No hardware,
network, firmware programming or device operations run.

From repository root:

```
uc-library/.venv/bin/python uc-library/candidates/large01_w02/checks.py format
uc-library/.venv/bin/python uc-library/candidates/large01_w02/checks.py compile
uc-library/.venv/bin/python uc-library/candidates/large01_w02/checks.py symbols
uc-library/.venv/bin/python uc-library/candidates/large01_w02/checks.py replay
```

Each non-format check compiles in fresh, retained, unbound worker scratch.
Replay regenerates native fixtures in that scratch and compares the canonical
fixture before executing the optimized host program. CMake's test invokes the
same replay adapter against the canonical role-linked executable and explicit
fixtures. Root retains global integration, current proof resealing and guarded
readiness admission. No ready/pending ledger fragments are supplied by this
worker; original declaration decisions remain with Root.
