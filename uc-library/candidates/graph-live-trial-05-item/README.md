# MeterManagerBase portable source port

Five original RM/RML mixer 13731 methods are implemented in their original
case-sensitive class scope. The original ELF and every original range are bound
in native-fixtures.json. Core implementation comes exclusively from pinned CCL
5.0.0, commit e8cbdea4a4a20e15111f5a690798a259c0374b31.

The port intentionally uses actual Core::Threads::Thread, Lock/ScopedLock,
CurrentThread::sleep and FixedSizeVector<int,100>. Original CoreThread/CoreLock
names differ. Portable inheritance, constructor, atomic stop/running state,
containers and field declarations do not establish original layout or ABI.
Original non-template return declarations are unencoded and remain unresolved.
The int threadEntry return uses CCL's declared interface and observed native zero.

Client state and virtual callbacks come from the explicitly independent
presonus::meter::Environment interface. It exposes original observed application
boundaries, not a fabricated ServerImplementation. Delivery invokes the real
source-port Presonus::UC::INetworkManager::sendEvent(const Event &, int) via a
borrowed reference supplied to the manager constructor; no unresolved send hook
is used. The native singleton getter is intentionally adapted to borrowed lifetime. tick/clientTick correspond to
observed virtual call slots, whose original declarations remain unresolved.
serverAvailable distinguishes an absent native server from the environment needed
for the unconditional meter tick. sendToClients requires an available environment
and valid native-equivalent event/list data and a live network provider. The environment and referenced
strings must outlive each operation; caller must serialize environment mutation.
Manager destruction during an active thread is outside this bounded contract.

oracle.py executes only original target instructions with Unicorn. It never
executes or reconstructs Core binary bodies. It stubs start/join/terminate/sleep,
locks, hasClients, network lookup, virtual callbacks/send, and strstr. Native
fixtures retain actual writes, external boundary observations and normalized
results/traces. Stack writes, lock calls, network lookup and strstr calls are
retained as raw evidence but excluded from normalized portable comparison;
portable tests invoke real CCL lock/vector code and capture application/thread
boundaries. A test-only INetworkManager captures sendEvent; unrelated services
abort if unexpectedly invoked. Production uses the existing real provider interface. The normalized comparison checks flag restoration/stop state, join
fallback, alternating tick phases/calls, client classification/truncation/order,
final event routes and per-delivery route/flag traces. Return register values
for void adaptations are intentionally excluded. No exception-unwind execution,
thread scheduling/timing equivalence, ARM object ABI or hardware proof is claimed.
Native hasClients is stubbed, not independently recovered by this work.

Replay accepts an explicit canonical executable and fixtures:

```
uc-library/.venv/bin/python uc-library/candidates/graph-live-trial-05-item/check.py replay --executable BUILD/graph_trial05_item_tests --fixtures uc-library/candidates/graph-live-trial-05-item/native-fixtures.json
```

Root owns shared CMake, readiness fragments and final admission. Proposed RM object
partition ownership follows the original server-only identity ownership in these
packets; no cross-role overlap claim is made. No shared build files were edited.
