# BeastPanelRegistrar::getTags portable reconstruction

Original: `_ZNK8Presonus5Panel19BeastPanelRegistrar7getTagsEiRi`, demangled
`Presonus::Panel::BeastPanelRegistrar::getTags(int, int&) const`, RM/RML mixer
13731 server ELF SHA-256 `9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07`.
The complete original `.text` range is address 500368, size 40, file offset
467600, SHA-256 `fba1fb4c083be623d62b3eed478fefc76d6d418f98ffddfe9c8d4ec6c5bf2182`.

The native conditional instructions accept precisely group 20, return address
3472468 and set the referenced out-count to 32. Other groups return zero and
leave the out-count untouched. The packet's unvalidated pseudocode incorrectly
suggests an unconditional store; the source port follows actual instructions
and actual native execution. The full 128-byte addressed table is compared,
including eight `0xffffffff` words. Its local mangled name `_ZL9g48vTagsA` occurs
three times in this ELF; the address and size distinguish this table.

`validate.py` rechecks the complete ELF hash, actual section mapping, original
function symbol/range/hash, literal cell and exact addressed table symbol/range/hash.
It formats source/header/test, checks formatter conformance, compiles the original
C++ scopes and confirms the exact original mangled function via `nm`.
It executes the actual 40 ELF bytes in Unicorn ARM mode and compares pointer
presence, count and all returned words to the compiled C++ method. Synthetic
this/r3 values, stack, count buffer and canaries are explicit; no surrounding
firmware is executed. Group coverage includes signed boundaries, values around
20 and 16 reproducible random groups. Four count sentinels give 120 comparisons.
The native count-buffer canaries remain unchanged. The ordinary C++ test also
checks repeated table identity.

The portable return `const std::int32_t*`, pointee constness, minimal class and
immutable private table are explicit source-port choices. Matching mangling
does not establish these original declarations, class layout, inheritance,
ownership, table mutability or ARM ABI. Return types are not encoded here.
Status remains original-declaration pending. No hardware validation occurred.

The first validation attempt stopped before compilation/native execution because
nonallocated debug sections overlapped the address lookup. Requiring SHF_ALLOC
corrected this. The second stopped before compilation/native execution on the
three same-name local symbols; exact address selection corrected this. The third
passed. `metrics.json` records these repeats; `commands.jsonl` retains subprocess
commands, outputs, durations and return codes.
