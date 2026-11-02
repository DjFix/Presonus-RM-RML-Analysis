ChannelComponent source-port regression

Run `replay.py --executable ABSOLUTE_BUILT_EXECUTABLE --fixtures native-fixtures.json`
from the repository root using `uc-library/.venv/bin/python`. Canonical CTest must
supply its built executable explicitly. The replay does not read operational
proofs or candidate paths. `native_oracle.py` regenerates observations from the
original hash-bound RM 13731 ELF using Unicorn; it never loads reconstructed C++.

The 52 input words are raw little-endian float bit patterns where specified:

| Index | Meaning |
| --- | --- |
| 0 | Target number 1..10 in dispatched packet order |
| 1 | Present-parameter bitmask for slots 0..13 |
| 2..15 | Parameter values: mute, pan, linked pan, level, solo, locate indicator, locate position, main assign, mono assign, solo mode, pan mode, reset comp, reset gate, reset eq |
| 16..17 | Stubbed normalized level and locate-position values |
| 18..20 | Initial three channel coefficients |
| 21..22 | Initial two solo coefficients |
| 23..24 | Initial gain and last fader-locate value |
| 25 | Removal boundary toggles active state |
| 26 | Virtual level update leaves solo dirty unchanged (0), sets it (1), clears it (2) |
| 27 | Fader-locate input |
| 28..30 | Reserved |
| 31 | Explicit pan-law NOBITS input |
| 32..39 | Link side, active, linked, solo blocks A/B, global/solo parameter providers present, pan-mode cache present |
| 40..47 | Eight update flags |
| 48..49 | Channel name state absent/default/custom; pair absent/no name/has name |
| 50..51 | Solo-mode cache present; available comp/gate/eq children bitmask |

The output vector contains return (-1 for intentionally unspecified void output),
three coefficients, two solo coefficients, gain, eight update flags, pan/solo cache
presence, final pan and indicator, whether partner acquired custom text, active,
then the event stream. Float outputs are exact bit comparisons. Events 1..8 are
linked query, remove link, partner lookup, fader dirty, main DSP change, solo DSP
change, virtual level update and virtual solo update. Events 100+slot/200+slot are
getValue/getNormalized; 300+slot is setValue followed by value bits and edit flag.
400..402 are comp/gate/eq child lookup; 500..502 are child reset followed by the
two boolean flags. Real CCL getter calls for lookup-created parameters are outside
the instrumented trace, while cache state and observable effects are compared.

Each fixture also retains native Core/app boundary arguments and non-stack memory
writes. Physical write ordering is not asserted against a portable C++ layout.
Core bodies are never entered: CCL 5.0.0 supplies the portable implementation;
synthetic native boundaries isolate the original application instructions.
Original libgcc soft-float instructions execute. `powf` is explicitly the shared
host libm boundary and does not validate original ARM libm. App link/DSP/mixer
provider internals, original declarations/layout/ABI, concurrency and hardware
remain outside the tested domain. Native-derived repeated level cases cover
unchanged coefficients and notification suppression.
