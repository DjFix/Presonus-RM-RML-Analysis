Original non-Core ARM fixtures and optimized portable C++ replay.

The oracle executes each selected app range in Unicorn. It traps CCL and
softfloat boundaries; it never executes or decompiles Core firmware bodies.
A recorded native operator-delete call is a boundary observation, not execution
of the original allocator. The host replay wraps real operator delete calls and
observes bitmap references from outliving objects. No destroyed C++ object is
read. D1 tests stop observation before manually freeing host test storage.

Coverage includes separate original constructor/destructor variants; draw bitmap
selection/source rectangles with initialized frame, valid focus bitmaps and
focus modes 1/2; ordinary/reversed thresholds; setFrame dirty transitions;
AllMutes activation; FileMute observer transitions and integer/fractional cache
selection. Cache status is null in these fixtures. Fractional cache values are
finite and representable as int64 after truncation. Core provider behavior and
portable layouts are intentional source adaptations. Hardware/ARM ABI,
exception cleanup and unencoded return declarations remain unverified.

FileMute activate/store require original mixer load/save/filter behavior absent
from the immutable selected app provider. They remain blocked, with no callback,
no-op implementation or generic Core persistence substitution.

Root must rebuild every dependent TU after integrating the enlarged partial
class definitions, retain the independent template default-call compatibility API for earlier findAttribute callers,
add only the new reconstruction200 CPP to COMMON, and retain canonical full
integration/readiness gates. The proposed CTest uses the sealed canonical fixture
and replay adapter with its built executable. Worker local checks use only owned
proposals plus immutable copied CCL archives and bound app timer/clock sources.

The default-call compatibility constructor is a separately labeled template API, not a recovered original default constructor. Its unbound parameter path throws; the preflight verifies prior findAttribute use and checked rejection.
