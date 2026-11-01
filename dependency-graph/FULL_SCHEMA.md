# Full graph data contract

Current source/compiler observations are separate from original ELF identities.
Source Function/Type/Data declarations describe the current port and pinned CCL,
not original firmware layout/return types or ARM ABI compatibility.

## Nodes

| Kind | Count |
| --- | ---: |
| CatalogSymbol | 51137 |
| Data | 218088 |
| Fixture | 373 |
| Function | 169001 |
| Proof | 133 |
| Test | 322 |
| TranslationUnit | 625 |
| Type | 30927 |
| UnresolvedCall | 62615 |
| file | 15860 |
| symbol | 2104 |

`CatalogSymbol` is keyed by the original catalog anchor: duplicate ELF/name ranges
remain separate. `symbol` is the original readiness key ELF SHA+mangled name.
`Function` includes source methods, template specializations and compiler ABI
variants; its count is not a count of independent algorithms. Local compiler
IDs have build-group scope; test main/definitions are qualified by source TU.
`TranslationUnit` carries the exact compile command/configuration. File roles
are also expressed by relations; one path can be both source and test input.

## Relations

| Kind | Count |
| --- | ---: |
| ALIAS_OF | 81780 |
| CALLS | 158275 |
| CATALOG_CANDIDATE | 2105 |
| COMPILED_AS | 625 |
| CREATES_LAMBDA | 461 |
| DECLARED_IN | 227413 |
| DECLARES_METHOD | 218712 |
| DEFINES | 2101 |
| DEFINES_FUNCTION | 149951 |
| ENCODED_NAME_MATCH | 5899 |
| FUNCTION_REFERENCE | 161589 |
| GCC_CALLS | 112571 |
| GCC_REFERENCES | 69770 |
| GCC_UNRESOLVED | 3209 |
| HAS_TEST_TU | 281 |
| HAS_TYPE | 44110 |
| IMPLEMENTED_IN | 17538 |
| INDIRECT_CALL | 59406 |
| INHERITS | 13217 |
| MEMBER_OF | 249021 |
| OVERRIDES | 26703 |
| RUNS | 322 |
| USES_DATA | 421015 |
| USES_FIXTURE | 430 |
| USES_TYPE | 552664 |
| VALIDATED_BY | 3156 |
| VIRTUAL_CALL | 12270 |
| compiler_input | 118942 |
| compiles | 625 |
| link_input | 2190 |
| proof_binding | 3933477 |
| validation_binding | 2104 |

CALLS = source-resolved call; GCC_CALLS = compiler pre-optimization call.
ALIAS_OF retains compiler variants. VIRTUAL_CALL/INDIRECT_CALL/GCC_UNRESOLVED
retain uncertainty; OVERRIDES gives candidates, not proven runtime receivers.
USES_DATA/GCC_REFERENCES do not claim complete memory alias or write analysis.
USES_TYPE/HAS_TYPE/MEMBER_OF/INHERITS retain source declarations.
FUNCTION_REFERENCE includes address/other source references, not only execution.
CREATES_LAMBDA does not assert invocation. DECLARED_IN/IMPLEMENTED_IN locate source.
HAS_TEST_TU/RUNS/USES_FIXTURE come from explicit CMake/CTest evidence.
ENCODED_NAME_MATCH/CATALOG_CANDIDATE are identity candidates, not ABI proof.
proof_binding/validation_binding/VALIDATED_BY are provenance, not code ownership.

Query seed resolution must distinguish an indexed Function from a catalog-only
symbol. An unmapped original symbol must be reported unknown rather than treated
as an independent leaf. Current case checker explicitly verifies its source seeds.

Reading-context policy is explicitly in full_queries.py. It does not silently
cross all whole-archive/proof bindings or solve runtime pointer aliasing. Preserve
unknown boundaries and escalate instead of presenting this as full firmware
semantic independence. Both graph services preserve the same input CSV hashes;
type counts and queried exact-ID sets were checked against SQLite.
