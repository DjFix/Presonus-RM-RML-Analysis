# Handoff

Implemented a real portable source port in original
`Presonus::Panel::BeastPanelRegistrar` scope. Root owns CMake registration,
full Linux integration, shared readiness schema/fragments, dry-run/admission,
tracker and final evidence archival. This worker has not admitted readiness.

Owned production files:

- `uc-library/src/Presonus/Panel/BeastPanelRegistrar.cpp`
- `uc-library/include/presonus/panel/BeastPanelRegistrar.hpp`
- `uc-library/tests/native_beast_tests.cpp`

Suggested root target: build the CPP once in the RM/server object partition and
add the public header to the explicit header list. The native identity is server
only in this packet; do not infer any client implementation from absent mappings.
A normal test can compile `native_beast_tests.cpp` with the production library.
The test runs without arguments and returns nonzero on failure; its two-argument
mode emits observations for the validator.

Exact reproducible command from repository root:

```
uc-library/.venv/bin/python uc-library/candidates/native-live-trial-02-beast/validate.py
```

Result: 120 native ARM/C++ differential cases passed, plus standalone C++ tests,
exact `nm` identity and project-local clang-format apply/dry-run. Full details,
source hashes, compiler/formatter identities, ELF/table ranges and explicit
unresolved declarations are in `NATIVE.json`; cases are in `fixture.json`.
No Core dependencies are introduced. Root must keep this symbol in the pending
ledger because original return declaration and class ABI are unresolved.

Only packet-selected context plus repository AGENTS.md and applicable REA skill
instructions were read. A request for readiness-schema examples was withdrawn:
Root retained admission ownership, and no graph expansion was needed. The
packet's native bytes supplied sufficient nonempty context for this method.
No unrelated proof bundles or global registry/tracker/build files were changed.
