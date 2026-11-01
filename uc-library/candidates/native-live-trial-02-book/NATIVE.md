# Book::isValidPos source port

The two exact original 60-byte ranges are identical without normalization:
client CS18AI 13840 and server RM/RML 13731, intersection 1/1 selected
method in each role. Each full ELF, section-relative range, packet file offset,
instruction bytes and range digest is independently checked. Original identities,
addresses, sizes, firmware and ELF hashes are retained in NATIVE.json.

The observed signed index check rejects negative or out-of-count positions,
null slot pointers return zero, and non-null slots return the unsigned byte at
pointee offset 5 without boolean normalization. The source port preserves that
behavior through an independent borrowed-state adapter backed by pinned upstream
Core::ConstVector. It does not recreate or assert the original object layout.
Borrowed slot arrays and six-byte pointees must outlive Book; pointers/count
must describe readable memory for accepted indices. No ownership is transferred.

The portable uint32_t return is deliberate; the original unencoded return type
remains unresolved. Member/non-const shape is consistent with r0 object and r1
index access, but matching mangling alone does not prove the original declaration,
layout, inheritance or ARM ABI. Both original identities remain pending, not ready.

validate.py executes the actual hash-verified ARM instructions with Unicorn,
then streams native results into compiled original-scoped C++. The domain covers
all 256 unsigned byte outcomes, null slots, negative indices including INT_MIN,
upper/excessive indices including INT_MAX, and zero/negative counts. NATIVE.json
records its exact domain, source hashes, formatter version and upstream dependency.
No hardware or invalid-address/concurrency behavior is claimed. The adapter uses
real upstream Core declarations; Core binary implementations were not recovered.
The pinned CCL root commit was checked with git show and has no parents.

The initial full replay used an independently hash-matching relocated ELF copy.
The final producer was changed to navigate native-context.json binaries/bodies
and replayed to bind the exact packet paths, offsets and instruction stream.
This was a packet-field navigation clarification, not missing ELF evidence.
commands.jsonl preserves exact producer commands, timestamps, durations and output;
metrics.json records reviewed paths and final timing. Root owns production CMake,
full integration, role audits and registry admission. This local proof alone is
not readiness admission or global integration proof.
