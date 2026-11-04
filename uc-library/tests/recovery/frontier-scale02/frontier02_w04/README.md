This offline test compares six constructor executions with actual ARM constructor
and ControlGroup base instructions. It invokes the current ControlGroup and CCL
containers in compiled C++; checks the independent inherited-control adaptation;
and intercepts LinuxTransfer's real ioctl boundary using the linker wrap option.
No real device call occurs. Both constructors perform no device I/O.

The original class's ARM layout and complete virtual inheritance are unresolved.
The new C++ is a portable source model, not an ARM ABI reconstruction. Native
vtable writes are captured separately and are not compared to host pointers.
The original constructor leaves transmit/receive buffers untouched; the portable
source model value-initializes them, as the existing independent API did.

Canonical CTest must execute replay.py with its built frontier02_w04_replay
executable and this directory's immutable fixtures.json. The fixture producer
oracle.py writes only the explicitly supplied new scratch output path; it must
never overwrite fixtures.json during acceptance. Root owns shared integration.
