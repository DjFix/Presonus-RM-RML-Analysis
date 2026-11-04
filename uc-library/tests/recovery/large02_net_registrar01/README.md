Owning ServerRegistrar / Server / RemoteServer portable lifecycle

The eight sealed packets bind sixteen exact original ARM ranges, including separate
Registrar C1/C2 and D1/D2 ranges. Native executions use Unicorn and both hash-checked
ELFs. Core Vector resize/destructor and runtime delete are explicit modeled
boundaries, never executions of original Core or libc. Destructor storage boundaries
unmap initialized modeled buffers; actual app instructions perform indirect remote
D0 dispatch, raw vptr writes and operator-delete calls. Fixtures retain all writes,
range offsets, hashes and modeled heap releases.

The host uses actual unchanged pinned CCL 5.0.0 vectors and StaticSingleton.
The driver replaces global new/delete only to record and physically malloc/free
real storage: expected events are never appended by a callback or destructor.
Exact D1/D0 entry names are called directly; deleting destructors physically release
both vector storage and object allocations. Registrar populated vectors contain
0/1/3/5 remotes with optional alternating nulls, with 0/3 storage entries. Server
and RemoteServer storage has 0/1/3/7 entries. Borrowed local/listener objects survive.
Native and host normalized traces agree in 100 per-ELF cases. A separate regression
checks borrowed Registrar state preservation and stable actual CCL singleton identity.

Owning RemoteServer() and Server() setup is independent source composition and
has no original constructor credit. Borrowed tagged constructors and borrowed
Registrar state remain a separate source domain. The fourth correlated metadata
view vector, ownership pointers, unique-ownership guard and uint32_t storage are
independent source choices, not inferred original fields or element types. The
remote-state owner is destroyed before the Server base; base cleanup only accesses
its own initialized CCL storage and does not dereference the borrowed metadata state.

No original full declarations, private layout, original ARM ABI, raw host vptr-store
trace equivalence, target libc/Core execution, concurrency/reentrant mutation,
allocation failure/unwinding, duplicate native owners or hardware behavior is
claimed. Host C1/C2 and Registrar D1/D2 can alias; every original range remains checked
separately. No nonexistent original Server/RemoteServer D2 target is credited.

Run checks.py format / compile / symbols / replay from the repository root.
Root owns production CMake integration, full Linux tests and readiness admission.
