# Stabilized UART diagnostic source port

The sealed two packets bind the local global `_ZL11dspUartTestv` and original
FrontPanelComponent::uartTest wrapper in RM13731. The helper remains a separately
emitted static global C++ function. The wrapper and helper are in one source TU.
Production uses existing UARTComm and real CCL DebugPrintf/system clock providers.
No synthetic successful callbacks exist in production.

The oracle checks the full original ELF hashes, exact symbol/section/ranges,
literal pool pointers and each NUL-terminated native string range. It executes
both the original helper and caller. UARTComm/libc/CCL calls are explicit boundary
models; the helper's ARM instructions and stack writes are observed independently.
No native UART/Core/hardware provider execution is claimed.

The host driver constructs the existing borrowed FrontPanel domain and invokes
the real source wrapper/helper. Link-time wraps intercept open/read/write/close,
ioctl, termios/raw/speed, fcntl and clock_gettime before invocation, and reject
unexpected device paths/descriptors. Real UARTComm, its lock lifecycle, CCL clock
arithmetic and CCL DebugPrintf formatting run. printf and fortified __printf_chk
capture the actual final debug provider output. The replay explicitly truncates
native debug call message strings at NUL to match the pinned CCL DebugPrintf ->
NUL-terminated DebugPrint pipeline; raw native call arguments and read-zero
observations remain unchanged. This is source-provider adaptation, not recovered
original Core behavior.

Cases cover successful bidirectional probe, both mismatch branches, discarded
sync junk/per-call timeouts, a timeout after synchronization and ignored short
write result. Original first-byte synchronization has no aggregate deadline:
perpetual no-response and failed-open nontermination are excluded, not repaired.
Host syscall error/termios failures beyond the selected fixtures and native
exception cleanup are not claimed. Source destructor invalid-handle close debug
messages are filtered from the application's explicit-close trace; actual POSIX
close events remain compared. Original ordinary return declarations/layout,
ARM ABI and hardware interoperability remain unresolved.

Local checks: `uc-library/.venv/bin/python uc-library/candidates/stabilized01_uart/checks.py KIND`.
Root places FrontPanelUartTest.cpp in the RM partition and includes the provided
CMake metadata. Local checks never admit global readiness.
