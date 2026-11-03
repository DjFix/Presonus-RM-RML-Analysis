The two OutputComponent methods are bounded portable source ports. They retain
encoded parameter identities in the existing original C++ class. Void returns
are chosen portable declarations, not recovered original return declarations.

The production binding extends the existing state with independent dirty flags
and mandatory application callbacks. The callbacks are invoked before derived
state changes and must implement the application's Channel behavior. No default
Channel implementation is supplied. Missing callbacks throw a logic error; this
is an intentional source-port failure contract, not original behavior.

The native oracle verifies all 25 full original ranges against ELF section
mapping and their packet hashes. It executes each original target with Unicorn,
records actual object writes and BL entry snapshots, and skips BL callees as
explicit boundaries. It does not execute base lifecycle implementations or
establish ownership or layout. Twenty-three lifecycle targets remain blocked;
their one-case native observations are research only. No deleting destructor is
claimed. Native C1/C2 ranges are distinct and checked separately.

The portable replay covers 576 paramChanged cases and 48 setSectionCoeffChanged
cases. Tags include both matching values and neighbors; messages include 3 and
nonmatching negative, bounded, and maximum integers; section indices include
zero, one, negative and integer extremes. Dirty/changed state is varied, and
callback mutation of tag and state checks sequencing. Parameter identity and
tag access use real pinned CCL NumericParam and Parameter::getTag. Mutation
changes borrowed ParamInfo storage while the parameter remains alive.

Root integrates the new CPP into one production partition and links the replay
driver to the resulting role archive. Canonical CTest must use the built driver
and these exact fixtures; the supplied CMake fragment never compiles the
production CPP again. Installed-role, full integration and registry admission
remain Root-owned. A local handoff never establishes readiness or ARM ABI.
