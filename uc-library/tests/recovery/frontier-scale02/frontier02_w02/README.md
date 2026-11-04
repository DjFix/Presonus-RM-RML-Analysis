Bounded FXBook C2 source port. The exact 60-byte ARM range (including literal)
is hash checked and executed in Unicorn. The Book(int) call is intercepted and
caller-saved registers clobbered; no native Book/Core implementation executes.
Native observations include ordered pointer stores, vtable literal store, this
return, original call arguments and untouched object sentinel bytes. Six cases
cover signed int boundaries, null/non-null, equal and opaque maximum pointers.
Portable replay invokes real current Book.cpp and its CCL fixed vector, checking
empty state separately from native constructor observations. FxPresetComponent
and Parameter are opaque borrowed identities and are never dereferenced.
Original full class, virtual table, inheritance, field layout, destructor,
C1 alias identity, ARM interoperability and hardware remain unproved. Public
inheritance and getters via an independent inspector are portable source choices.
