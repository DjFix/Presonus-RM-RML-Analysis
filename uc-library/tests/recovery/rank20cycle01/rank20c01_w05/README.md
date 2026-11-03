# FilterGroupManager source-port lifecycle

The production class derives from real pinned CCL Component. This is an intentional
portable source adaptation, not proof of complete original inheritance, virtual
interface, layout or ARM ABI. Original constructor calls Component with the name;
original nondeleting destructor calls Component cleanup. The only additional
observed app writes set its virtual dispatch pointers. Portable C++ delegates
these compiler-managed details to the host compiler.

oracle.py executes original app instructions on Unicorn with mapped original ELF
segments. A test-only Core boundary capture records call identity, arguments and
app vtable writes, then returns with memory unchanged. No Core instructions are
executed or reconstructed. Six native cases cover caller sequencing with three
initial object byte patterns. These do not prove native Core lifecycle behavior.

driver.cpp independently compares the adapted class to actual pinned Component:
four names (including truncation), default parent/children/parameter counts, and
three owned-child counts (0/1/3). Child destructors actually run. It does not test
child arrays, owned-by-array, parameter cleanup or whole FilterGroupManager use.

Canonical CTest must invoke replay.py with the canonical built executable and
explicit fixtures.json. Root integrates the production CPP into RM OBJECT once.
No readiness fragment is supplied; Root creates it after shared integration.
