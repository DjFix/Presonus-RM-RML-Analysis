# Frontier small01 worker 02

Four partial portable source ports retain the exact selected RM/RML 13731
symbols. Rack composes the existing MixerComponentBase implementation. Send
composes the existing OutputComponent implementation and mutates the same output
binding states used by child components; it samples the tag before calling base.
GlobalComponent and GEQLinkHandler use the actual pinned CCL Component destructor.
These are source-port choices, not complete recovered class declarations.

`oracle.py` verifies all four ELF ranges by section mapping and SHA-256, then
executes their original ARM instructions with Unicorn 2.1.4. Its BL interceptions
are bounded call contracts: no Core firmware body executes. It records native
writes, call arguments, states at calls and native vptr values. Output interception
models its existing source semantics and a Channel callback mutation contract;
the executable independently runs the actual existing Output source.

The fixture has 1,940 native executions. Rack uses master/slave results, 0/1/3
channels and initial 0/7/UINT32_MAX state. Send uses signed tag extremes and branch
boundaries, five messages, 0/1/3 nonnull children, initial 0/7 words, both dirty
bits and callback mutations. It compares state before callbacks as well as final
self/child dirty words. The executable performs 1,938 app replays, 18 direct-base
naming runs and nine actual Component/Global/GEQ lifecycle runs. Rack naming uses
real ChannelComponent instances, required identity/parameter bindings and real
CCL string parameters; both default and custom names are checked. Lifecycle
observations count actual child destructors, child deallocation, array destruction
and array deallocation from the real CCL provider. Native D1 boundary observations
and provider observations remain separate. No native D0, full native hierarchy,
return declaration, ARM ABI or hardware claim is made.

Checks from repository root:

```
uc-library/.venv/bin/python uc-library/candidates/frontier01_w02/checks.py format
uc-library/.venv/bin/python uc-library/candidates/frontier01_w02/checks.py compile
uc-library/.venv/bin/python uc-library/candidates/frontier01_w02/checks.py symbols
uc-library/.venv/bin/python uc-library/candidates/frontier01_w02/checks.py oracle
uc-library/.venv/bin/python uc-library/candidates/frontier01_w02/checks.py replay
```

All outputs go to the assigned scratch. Root owns production RM partition
integration, canonical Linux CTest, installed-role/compile-once checks, fresh
active-source proof, guarded SQLite preflight/admission and tracker/mirror updates.
No readiness fragment is admitted by the worker-local proof.
