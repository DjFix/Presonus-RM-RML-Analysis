# Display commands and color mapping: bounded source port

The production declarations retain original Presonus scopes and parameter types,
using actual pinned CCL 5.0.0 Color and TRect headers. The source model borrows
SpectrumPainter rectangle state and DisplayCommandList state explicitly; these
constructors and backing members are source-port interfaces, not recovered
original object layouts or lifecycles. Original ordinary return types remain
unresolved. Native register use establishes that ColorMapping methods are static.

Commands contain 20 bytes. Opcode occupies byte 0, positions occupy little-endian
halfwords at 4/6/8/10, and color occupies RGBA bytes 12..15. Unwritten bytes remain
unchanged. Appending at count 49 creates record 50, while count >49 is unchanged.
The bounded source model covers nonnegative counts and valid backing storage.
Negative native counts, invalid pointers and address wrapping are excluded.
Flush resets count and the separately observed auxiliary cursor, preserving all
command bytes. It has no original external calls and performs no hardware I/O.

The native oracle verifies the complete ELF SHA-256 and every selected original
range against its actual ELF section/file mapping. Unicorn executes the exact
original application instructions plus actual ELF libgcc soft-float instructions;
it neither executes Core firmware methods nor substitutes new C++/pseudocode as
expected values. Execution is restricted to selected ranges and libgcc arithmetic.
Original calls, non-stack memory writes and output memory are retained in fixtures.

The portable driver compares complete command buffers, count/cursor state,
rectangle copies and bit-exact distance values. The floating-point domain is
finite values; NaN, infinity, non-default rounding and hardware are excluded.
No original class layout, ARM ABI compatibility, allocator ownership, complete
SpectrumPainter implementation, device interoperability or readiness is claimed.

Each check creates a fresh directory below the assigned project scratch and
records its exact compiler/replay commands, UTC timestamps, duration and output.
The canonical CTest adapter runs replay.py against the coordinator's actual built
executable and explicit fixtures.json. Root owns production partition selection,
full Linux integration, readiness fragments/admission and global trackers.

The palette is the genuine table produced by executing the original application
initializer at 0x75340 (1588 bytes), with its complete 476-byte result and all 17
referenced names retained. Production stores the observed names, colors and
bit-exact stored HSL constants. It retains stored values rather than recomputing
HSL from the palette colors. Mapping tests retain original pointer values and
normalize them to the observed strings when comparing host results. The portable
mapColor return is const char*; original pointer return declaration and character
const qualification remain unresolved. The portable mapColorToEnum uses uint32_t;
its original named return enum remains unresolved. The native methods ignore
alpha for nearest-color selection.

Final coverage is 650 fixture cases: 20 rectangle copies, 168 individual command
operations, 12 sequences of 70 operations, 160 distance comparisons and 290 color
mappings. Source compilation requires ordinary IEEE binary32 arithmetic,
-ffp-contract=off and -fno-fast-math; apply these to the production TU as well as
the replay driver. The checks use optimized -O2 compilation. No readiness ledger
or admission fragment is produced by this worker; the handoffs provide local
proof for separate global integration and declaration review by Root.
