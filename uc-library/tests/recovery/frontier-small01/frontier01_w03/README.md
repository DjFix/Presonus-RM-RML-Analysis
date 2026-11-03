# Frontier small01 worker 03

Partial portable source implementations in the exact `Presonus::PotControl`,
`Presonus::FocusHelperButton`, `Presonus::FileMuteGroup` and
`Presonus::McuVpotControl` scopes, using pinned CCL 5.0.0. Original ELF identities
are preserved independently in each packet and HANDOFF_01 through HANDOFF_07.
Root assigns the mixed client/server CPP to COMMON exactly once.

`oracle.py` verifies each original ELF SHA-256, section mapping, file offset,
full symbol size and range hash before executing ARM instructions with Unicorn.
It excludes every Core instruction. Direct Core calls are intercepted at their
original target addresses, with recorded argument words, names and supplied
results. The object memory writes and complete executed application instruction
addresses are retained per case. This bounds observations to application logic
under controlled provider contracts, not firmware Core behavior or ARM ABI.

The 817 observations cover 729 old/new triples of bitmap identities (including
null, repeated and shared identities), five option strings, varied initial flags,
frame-count retention on null image, bitmap use counters; missing/non-string/
empty/nonempty viewName; attribute trees at depths 0, 1, 2, 7 with missing, scalar,
nested and null inputs; and six observations for each of four separately checked native constructor
ranges. Only FocusHelperButton consumes the varied int argument; PotControl and
McuVpotControl repeat the same rectangle/null-parameter boundary with varying
unused caller register r3. These repeats do not expand their input coverage. C1 and C2 native addresses/range
hashes remain distinct. Provider constructor interception supplies explicit base
state and null Parameter pointers, rather than executing firmware Core.

`driver.cpp` independently executes the actual pinned CCL constructors,
View/RadioButton attribute handling, Attributes storage and traversal,
BitmapManager lookup, and BitmapReference ownership. Test-only catalog seeding
calls real protected BitmapManager insertion through a legal member pointer;
it does not replace the production provider. Provider radio values, rectangle
forwarding, null parameter forwarding and actual provider reference cleanup are
asserted separately from the original-instruction comparisons. A live real CCL
NumericParam is also shared by real RadioButton/Slider and then by the portable
FocusHelperButton/McuVpotControl pair: nine provider and nine portable snapshots
check getParameter identity, observer-list membership/counts, disable/enable
notifications and nested scope-exit removal. This source-provider test adds no
claim about an unselected native destructor. Scope-exit
reference cleanup is a source-port observation, not evidence for an unselected
native destructor. The replay converts raw 32-bit frame-count words to the
portable signed int domain explicitly.

Partial portable state names and observation methods are independent APIs.
Complete original fields, original unencoded return declarations (notably bool
versus int for findAttribute), ownership beyond observed bitmap reference and
borrowed viewName behavior, vtable contents, binary compatibility, inherited
unselected app methods and hardware behavior remain unresolved. viewName borrows
Attributes storage; callers must preserve its lifetime. Valid traversal inputs
are finite, acyclic trees. No hardware or firmware programming operations run.

Root integration: add the production CPP once to COMMON and the public header
list; add this test directory. `frontier01_w03_replay` links `presonus_uc` and
CTest runs `replay.py --executable <canonical-executable> --fixtures fixtures.json`.
Native oracle replay is an additional acceptance check with a 600-second bound.
Global CTest, role/archive audit, active source evidence, SQLite preflight and
admission belong to Root. These worker handoffs are not readiness admission.
