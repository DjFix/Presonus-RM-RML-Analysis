# Global temporary scene path and FX parameter source ports

Production: `src/Presonus/frontier02/frontier02_w05.cpp`, RM-only OBJECT partition.
Public declaration remains `include/presonus/frontier01/frontier01_w02.hpp`.
Root owns production group, installed header lists, canonical integration and readiness.

Global retains actual CCL Component lifecycle and inherited constructors. Its new
borrowed mixer binding must outlive calls. Unbound path lookup throws a source-port
precondition exception. The implementation invokes actual existing getDataDir with
native literal `temp`, then pinned CCL FileName::descend with `mixer.scene`.
Replay verifies actual directory creation and no scene-file creation for three
folder choices; filesystem/provider failure policy and empty application-root
fallback are outside this domain.

FX constructs actual SendOutputComponent with the identical Output/SendState/child
bindings used by its own post-call stores. SendState gains trailing independent
fxChanged state (native store +0x194), preserving old aggregate initializers.
It reads Parameter::getTag after Send, matching native instruction order, and
for changed tag 410 sets own pending plus each child's fxChanged/pending.

Oracle executes each exact hash/section/range-verified original app target and the
bound expanded native Send dependency body.
Global callees are intercepted to record call arguments/literals. Output is a
fixture-only tag-mutation boundary; no native Output/Channel body executes.
Replay independently runs actual compiled Output+Parameter for each case,
then applies the native Send and FX store observations to that baseline and
compares actual Send and FX executions separately. It checks the Channel callback's identity, argument and
pre-call state observations too. Expected Send and FX stores originate in original ARM
instructions, never reconstructed C++ or pseudocode. Actual dependency behavior
is a preferred source-port provider domain, not an original firmware assertion.

Inputs: ten tags including 14/21/400/409/410/411/412/413, messages -1/0/2/3/4,
0/1/3 nonnull children, initial 0/7, pending false/true, no callback mutation or
mutation to 410/14 plus deliberate own-state changes. Tests use valid live
parameters and coherent unchanged child collections. Invalid pointers, vector
mutation/rebinding during callback, original complete declarations/return types,
original inheritance/fields/layout, ARM ABI and hardware remain unresolved.

Canonical CTest must invoke replay.py with its built driver and explicit immutable
fixtures.json. Local checks use copied immutable support archives; generated
executables/objects and replay filesystem output are unbound per-run scratch.
No global readiness fragment is admitted by this worker handoff.
