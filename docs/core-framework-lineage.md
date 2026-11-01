# CCL Core lineage and API comparison

Recorded: 2026-10-26. Scope: the Core framework in the CS18AI surface and RM mixer
Linux applications. This report records a read-only comparison performed in a
side conversation and the user's subsequent implementation direction.

## Finding

The applications have strong evidence of common lineage with the official
[Crystal Class Library (CCL)](https://ccl.dev/) Core library. Exact original
mangled function names match across a broad set of classes, including buffers,
containers, parameters, components, attributes, streams, JSON and surface GUI
classes. The historical firmware release or vendor branch has not been identified.

Official sources:

- [CCL framework repository](https://github.com/cclsoftware/ccl-framework).
- [CCL documentation](https://cclsoftware.github.io/ccl-documentation/).
- [Compared Core tree, CCL 5.2.0](https://github.com/cclsoftware/ccl-framework/tree/66cb50a6b0e3991d3ead8d7ffdcefc46654584ae/core).
- [Earliest release in the captured public history, CCL 5.0.0](https://github.com/cclsoftware/ccl-framework/commit/e8cbdea4a4a20e15111f5a690798a259c0374b31).

## User-selected implementation direction

The user explicitly requested:

1. Base Core reconstruction on the earliest publicly available version and the
   actual method source code.
2. Prefer the source implementation over the implementation inferred from the
   binary, including where they differ.
3. Have the main agent delegate a subagent to add the official repository as a
   Git submodule under `third_party/`, skip manual reconstruction for matching
   prototypes/APIs, and recover the remaining app-specific functions.

The captured seven-commit public history begins with CCL 5.0.0, dated
2026-01-12, at `e8cbdea4a4a20e15111f5a690798a259c0374b31`, whose recorded parent
list is empty. This is the baseline candidate to verify and pin from Git. It is
not evidence that the firmware used CCL 5.0.0. The comparison below used CCL 5.2.0
and must be repeated against the chosen early baseline before defining its
function-skip list.

For matching APIs, provide implementations through the upstream submodule rather
than duplicating or manually decompiling Core methods. Preserve the original ELF
symbol records and link them to the chosen upstream commit, declaration and
implementation. Use an explicit upstream-provided/source-port status; do not
automatically promote them to original-behavior-verified or ARM-ABI-compatible.
For differing APIs, prefer upstream Core and make explicit application-side
adaptations. Preserve original namespace and mangled identities for app-specific
reconstruction. Retain upstream license and attribution notices.

The direction and results were sent to the main task, **Extract UC client and
server sources**, thread `01a17910-caf1-7012-934c-607ed1db6a6f`. This report does
not assert that submodule integration or the delegated reconstruction is complete.

## Compared inputs

### Reproduced early-source baseline

The main workflow subsequently registered `third_party/ccl-framework` at the
verified official Git root/tag `ccl-5.0.0`, commit
`e8cbdea4a4a20e15111f5a690798a259c0374b31`, on both Mac and VM101. No commit or
push was made. The first full checkout failed with RPC EOF; after it terminated,
a sparse `core/build` checkout succeeded. All 413 selected Core files were
verified against their Git blob identities. Upstream files remain unchanged.

The reproducible matcher uses libclang 17, `armv5te-unknown-linux-gnueabi`, C++17,
and a real project-local Linux armel sysroot plus actual PNG/DNS-SD development
headers. No fabricated Core/PreSonus definitions or libc API stubs were needed.
Of 372 C++ units, 282 parsed successfully with function bodies; non-target and
remaining dependency failures are recorded, not treated as matches.

| Original binary | Core functions | Exact encoded-interface matches | Upstream bodies available | Declaration/synthesized only |
| --- | ---: | ---: | ---: | ---: |
| CS18AI 13840 | 2,374 | 1,566 | 1,467 | 99 |
| RM 13731 | 1,596 | 945 | 890 | 55 |

These are source-provider/skip-list records, **not binary-behavior-verified
functions**. Full original return types and layouts are not established by
mangling. Template bodies are linked through generic definitions and their
source extents; constructor/destructor variants remain separate original
symbols. Fifty-one client and ten server differing-mangling API adaptations
are candidates, not exact matches. An unmatched symbol is not automatically
application-specific or proven absent from the framework.

Artifacts: `temp/recovery-package/uc-library/validation/core-upstream/source-map/`.
The immutable baseline is under
`evidence/recovery/2026-10-26/core-upstream/baseline-5.0.0-01/`; its manifest
SHA-256 is `7d19b9e6bc3fb791381dc7652036d337d3f32133a791f9710a6d4e442d04548d`.
The main symbol generator independently checks all pinned source-file SHA-256
and Git blob identities, original ELF/address/size mappings, and direct or
generic body extent hashes before displaying source availability.

Actual upstream `corelib` has also built successfully on Linux VM101 with
system PNG/Zlib/DNS-SD dependencies and no vendor patches. Per-method native
linkage, allocator/clock smoke tests, original ARM ABI and hardware behavior
remain separate validation scopes. The later 5.2.0 investigation below is
historical context and must not be used as this baseline's mapping.

| Input | Version | SHA-256 |
| --- | --- | --- |
| CS18AI surface | 13840 | `304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0` |
| RM mixer | 13731 | `9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07` |

Local ELF copies used:

- `temp/uc-recovery/inputs/surface-13840.elf`.
- `temp/uc-recovery/inputs/mixer-13731.elf`.

Compared upstream commit: `66cb50a6b0e3991d3ead8d7ffdcefc46654584ae`, CCL 5.2.0.
All 390 Core source/header files fetched for the comparison matched the Git blob
hashes in the previously captured complete repository tree.

## Method and coverage

- Used Apple libclang 17.0.0, target `armv5te-unknown-linux-gnueabi`, C++17, to
  obtain mangled names from upstream declarations and referenced specializations.
- Considered all 263 Core headers. All 170 outside `platform/` and 41 platform
  headers parsed without errors. All Linux, POSIX and generic platform-interface
  headers were covered; the remaining 52 platform headers were outside the
  successfully parsed target/dependency set, including other operating systems.
- Additionally parsed 76 of 127 `.cpp` files without errors for declarations not
  exposed by public headers. Unparsed implementation units included foreign
  platform and external-library dependencies; their private declarations are not
  claimed as fully covered.
- Examined 93 candidate concrete template-class specializations: 84 parsed;
  nine depended on unavailable or changed types. Explicit class instantiation
  alone did not expose member manglings through libclang, so callable probes were
  used for the actual name comparison.
- Ran 206 concrete template-callable probes using `decltype` and declared
  argument types: 205 parsed successfully. The remaining probe required the
  app-specific `DefaultMeterInterpolator`. A successful probe contributes an
  exact match only when the referenced declaration's mangled name equals the
  original ELF name.
- Accounted for constructor/destructor variants returned by libclang. Remaining
  implicit variants, compiler thunks and function-local symbols stay separate.
- Independently re-read the original ELF32 symbol tables and verified each
  counted Core name and its address/size pair against the source ELF. Rechecked
  both ELF SHA-256 values.

The Mac had no Linux ARM sysroot. Minimal libc/POSIX and external type declarations
were supplied only in memory for syntax analysis, together with generated build
metadata placeholders. Core API declarations came from the hash-verified upstream
files. The analysis used skipped function bodies and, for callable probes,
disabled access checks. It was not a full framework build, execution test, layout
comparison or reconstructed-firmware version test.

## Results

Counts below are unique mangled function names per ELF, including template
instances, function-local symbols and compiler thunks. They are not a count of
reconstructed or behaviorally validated functions. The broader ownership filter
includes template functions with demangled return prefixes and thunks; earlier
counts restricted to demangled names beginning literally with `Core::` were
2302 surface and 1551 mixer and use a different denominator.

| Category | CS18AI 13840 | RM 13731 |
| --- | ---: | ---: |
| Original Core unique function names | 2374 | 1596 |
| Exact upstream mangled-name matches | 1468 | 879 |
| Matched class/template families | 184 | 113 |
| Additional matched namespace scopes | 7 | 3 |
| Unmatched: templates involving app-specific types | 367 | 371 |
| Unmatched: other templates | 68 | 20 |
| Unmatched: compiler thunks | 56 | 30 |
| Unmatched: function-local symbols | 87 | 78 |
| Unmatched: destructor ABI variants | 144 | 82 |
| Unmatched: same callable name without exact mangling | 24 | 12 |
| Unmatched: other methods without an exact declaration | 39 | 5 |
| Unmatched: scope without an exact class match | 121 | 119 |

The eight unmatched categories plus exact matches sum to the original unique
function-name total in each ELF. Class/family and namespace counts are separate
descriptive metrics, not additional functions.

Exact matches grouped by the upstream file containing the declaration:

| Upstream directory | CS18AI | RM |
| --- | ---: | ---: |
| `core/public/` | 268 | 252 |
| `core/portable/` | 988 | 529 |
| `core/gui/` | 107 | 0 |
| `core/text/` | 85 | 78 |
| `core/system/` | 18 | 18 |
| `core/network/` | 2 | 2 |
| **Total** | **1468** | **879** |

Examples of matching interfaces include `Core::IO::Buffer`,
`Core::IO::MemoryStream`, `Core::IO::BinaryAccessor`, interpolators and formatters,
`Core::Portable::Parameter`, `NumericParam`, `AliasParam`, `Component`, `Attributes`,
`AttributeQueue`, `FileIOManager`, `ZipPackage`, JSON readers/writers, and surface
views and graphics. Zero matches in a source group does not prove that all
related functionality is absent from the ELF.

## Observed API differences from CCL 5.2.0

| Original ELF interface | Compared upstream interface |
| --- | --- |
| `FloatFormatter(const char*, const char*)` | `FloatFormatter(const char*, int, const char*)` |
| `Component::resetToDefaults(bool, bool)` | Adds `const IStorageFilter*` |
| `FileUtils::getHomeDir()` | Takes output `FileName&` |
| `FileUtils::getTempDir()` | Takes output `FileName&` |
| `FileUtils::getDataDir(bool)` | Takes output `FileName&` before the flag |
| `Json::Parser` constructor with three pointer arguments | Adds a `bool` argument |
| `Json::Parser::readString(TextBuffer&)` | Adds a `bool` argument |
| Surface bitmap drawing methods | Several upstream overloads add `const BitmapMode*` |
| Surface text-input and keyboard methods | Additional capitalization argument and changed enum scopes |

Other nonmatching scopes include legacy `Core::Sockets::CoreSocket`,
`Core::Sockets::CoreNetwork`, `Core::Threads::CoreThread`, `CoreLock`, `CoreSignal`,
`CoreReadWriteLock` and `Core::Portable::ComponentBuilder`. Their absence under
the exact old names is not a finding that the corresponding functionality was
removed; renaming, aliases and architectural changes need separate mapping.

## Interpretation and limits

The breadth of exact matches is strong CCL/Core family-lineage evidence. It does
not identify an exact firmware-era release, exclude vendor changes, or prove
that all public CCL subsystems were linked into either application.

Ordinary non-template mangling generally omits the return type. Matching names
also do not prove class fields, inheritance, ownership, calling-convention
details, enum values, semantic equivalence or ARM32 binary interoperability.
Use upstream return declarations as the preferred source-port contract under the
user's direction, while distinguishing them from independently established
original ELF declarations. Review and test behavior at the application boundary.

An unmatched name is not automatically a changed API: template substitutions,
implicit destructors, compiler-generated symbols, private helpers and moved or
renamed scopes are separate cases. Do not classify all unmatched symbols as
app-specific code or all matching names as behaviorally verified.

## Existing evidence and follow-up artifacts

Previously captured source-lineage material is under:

- `temp/recovery-package/uc-library/validation/source-lineage/`, including
  `public-tree.json`, `public-commits.json`, `reference-files.json`,
  `declaration-candidates.json` and `README.md`.
- `temp/source-lineage/ccl-framework/`, containing the earlier partial reference
  snapshot with notices.
- `evidence/recovery/2026-10-26/source-lineage/`.

The full side-conversation comparison ran in memory. Its raw tool output is in
the conversation; it did not create a new machine-readable per-symbol report,
maintained matcher, complete on-disk upstream checkout or readiness seal.
This Markdown report preserves the findings, not those missing artifacts.

The delegated integration should produce a reproducible matcher and per-symbol
upstream/skip/adaptation mapping against the chosen early submodule commit, save
new logs and proofs under project `temp/` and structured `evidence/recovery/`, and
update `SYMBOLS.md` with source provenance and explicit validation scope. Preserve
existing completed work and the deferred hardware-testing boundary.
