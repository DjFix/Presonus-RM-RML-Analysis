Panel bounded source-port replay

The oracle executes original RM 13731 ARM instructions in Unicorn. All four
ranges (three targets plus SPI bitBang dependency) are independently verified by
ELF section mapping and full range SHA-256. Original PT_LOAD segments are loaded.
Core binary implementations are never reconstructed/executed.

Cache: 42 cases cover signed index extremes, zero/one/three entries, null items,
and actual reads from the original error symbol. Core error objects are verified
four-byte SHT_NOBITS symbols. Initial zero and explicit injected sentinel states
are separate bounded observations; no full-application sentinel lifecycle claim.
Production delegates to pinned CCL ConstVector::at.

Geq: 90 cases cover negative/current 0–5/extreme selections, main empty/first,
aux empty/valid/out-of-range, negative supplied counts and native error reads.
ChannelSelection is an independent binding to real CCL main/aux vectors and
geq count. Original field types/layout and pointer return declaration are pending.
Existing Dependencies remain unchanged. Root-authorized same-class caller edits
use the recovered selector when configured and keep the legacy assignedChannel
boundary before configuration. The test binds legacy boundary and CCL vectors
consistently to native observations, checks updateStereoField in both modes and
through the transition, and checks both updateStereoLink modes for null selected
channels. Unrelated app dependencies throw.
New selector requires a binding for nonnegative selection and throws if absent.

SPI: 192 cases cover dirty 0/1, descriptor -1/7, byte lengths -1,0,1,2,3,4,5,8,
and 0/1/3/17/41/65 controls. Nonzero control words include high-bit-set values.
The original onIdle and bitBang both execute. Only ioctl is stubbed: its actual
32-byte transfer descriptor, tx bytes and zeroed rx bytes are captured; the stub
writes 0xa0+i rx bytes and returns -1. No device is opened/accessed. The source
port encodes the observed payload and requires a caller-provided Transfer sink;
its test double mirrors that explicitly bounded ioctl behavior. BitBang return
is ignored by onIdle. Original onIdle ordinary return remains unresolved (chosen
void port declaration); native r0 values are recorded but are not declared equal.
Dirty state and final tx/rx bytes plus transfer fd/request/length are compared.
Native write events and incoming bitBang payload are retained in fixtures.
The source port avoids a native extra pointer-array read at the payload limit;
invalid pointer arrays, concurrency, syscall semantics and hardware are excluded.
Lengths above 8 are rejected by port construction to avoid native payload
stack-overflow behavior; negative/unsupported lengths clear dirty without a call.

Cache/channel/control types and storage are source-port declarations; no original
class fields, inheritance, ownership, lifecycle or ARM32 ABI fidelity is claimed.
Symbolic pointer tokens are never dereferenced by the portable test. Compiler
mangling equality establishes encoded identity only. No readiness is admitted.

Root integration: add all three new CPP files exactly once to RM OBJECT partition,
list public headers, add this test subdirectory, then replay against canonical
ranked09_panel_replay and explicit fixtures. The CMake file links the canonical
RM archive; no duplicated production source bodies are added to the test target.
