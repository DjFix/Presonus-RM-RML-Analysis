Bounded source port: MixerComponentBase::removeDelegate

The production method uses pinned official Core::Vector::remove; no Core binary
implementation is reconstructed. The complete existing MixerComponentBase
portable state model gains a delegate vector and an incomplete nested Delegate
declaration. No original layout, inheritance, lifecycle or return declaration is
claimed. The void return is an intentional source-port choice (compiled pending).

The test completes the opaque Delegate type only for test identity objects.
Sixty original ARM executions span empty, singleton, multi-element, duplicate,
first/middle/last/absent targets and both zero and nonzero error-slot payloads.
The oracle executes the complete exact ELF range under Unicorn, using controlled
memory, no external stubs. It records count, entire initial-length backing array,
read/write traces and actual error-cell reads. Synthetic nonzero error-cell state
checks consumer behavior, not original startup initialization. SHT_NOBITS initial
zero is loader modeling; no application startup or concurrency is executed.

Replay compares count and full backing storage. Portable allocator/stack writes,
original register residue and return r0 are outside the domain. Pointer identities
are normalized explicitly to fixture indices; original memory addresses are not
portable object layout. No hardware, ARM ABI or original C++ declaration verified.

Root must assign MixerBaseLinks.cpp once to RM/server partition, add this public
header explicitly if needed, and bind CTest to the canonical built replay target.
The proposed CMakeLists.txt links the verified presonus_rm_components facade.
No shared build files changed.

Resumed supported methods

OutputComponent::soloUpdate uses the already established ChannelState
soloCoefficients and input_port::Property model. Its required opaque resolver
matches the existing Input/Master source-port pattern; MultiParamProperty remains
incomplete in production. The test completes only an opaque identity token and
validates the resolver receives that exact token. Fifty-four original executions
cover unchanged/changed caches, signed zero, NaN, infinities and subnormal values,
with property counts 0, 1, 58, 59, 60 and 61. Original soft-float helper code is
executed without comparator stubs. Replay compares both cached bit patterns,
count and all 60 property entries; original call and write traces are retained.
Negative property counts are excluded and throw in the port to avoid invalid
portable array accesses; native negative-count behavior is not claimed.

MixerComponentBase::getLinkableChannelPair uses actual Core vectors and a required
independent channelIdentity query. It is an intentional source-port boundary,
not a recovered original Channel field or class definition. A missing query
throws logic_error. The native oracle observes actual channel offsets +0x16c and
+0x170, exact XOR/branch behavior, selected vector reads, and error-cell payloads.
Three hundred twenty original cases cover type 0, 4 and unsupported types,
empty/nonempty input and mix vectors, negative and extreme signed indices, and
null/nonzero error payloads. Portable tests use pointer identity tokens that are
never dereferenced; the native oracle uses separately controlled mapped memory.
A separate adapter test confirms missing bindings throw; it is not an original
execution claim. Original ordinary returns/layouts/ARM ABI remain unresolved.

ChannelComponent::paramChanged has no existing implementation/provider contract
in the supplied full source; OutputComponent::paramChanged remains blocked.
No no-op implementation or fake Core classes are provided.
