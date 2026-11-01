DAW FX portable source port, trial 05
==================================

All five original names are defined in Presonus::Surface::DawFxPageComponent.
Original return declarations remain unresolved. In particular the native
getListOffset address result cannot distinguish an int pointer from a reference;
the portable API deliberately uses int&. Constructor, fields and binding record
are independent portable source contracts, not recovered ARM class layout.

The mode provider is the pinned official CCL Parameter API. The executable tests
use real CCL NumericParam and AliasParam with a test observer that records value
reads. No production Core implementation or fake Core class is introduced.
Independent application callbacks represent the unresolved folder existence,
used-count and list-refresh boundaries. Callbacks must be non-null and valid for
the lifetime of the component. The native oracle intercepts those boundaries.
It executes the five original methods, including their mutual calls, and checks
both offset slots, selected address identity and ordered boundary traces.
The float conversion helper and parameter virtual call are intercepted, with
finite representable mode values only. Their implementation is not verified.

Original symbol ranges include the getMaxListOffset division literal. ELF SHA,
section mapping, offsets and per-range hashes are retained in fixtures.json.
Expected observations come from Unicorn executing original instructions, not
from reconstructed C++ or decompiler pseudocode. Original and portable execution
counts are reported separately in results.json. Hardware, ARM object layout,
unbounded inputs, callback reentrancy and updateList internals are excluded.

Replay against the canonical executable:

uc-library/.venv/bin/python uc-library/candidates/graph-live-trial-05-dawfx/validate.py replay PATH_TO_EXECUTABLE uc-library/candidates/graph-live-trial-05-dawfx/fixtures.json

Proposed CMake production partition: CS18 only; source compiled once. Public
header: include/presonus/surface/DawFxPageComponent.hpp. Test target:
graph_trial05_dawfx_tests. C++20 and -fno-rtti for the test are required by this
local implementation/provider build. Root owns integration and readiness.
