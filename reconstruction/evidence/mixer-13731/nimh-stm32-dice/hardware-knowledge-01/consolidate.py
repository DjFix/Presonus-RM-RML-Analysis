from pathlib import Path
import json,hashlib,gzip,os,re,datetime
from urllib.parse import unquote
R=Path.cwd().resolve();H=R/'reconstruction/hw';E=R/'reconstruction/evidence/mixer-13731/nimh-stm32-dice/hardware-knowledge-01';E.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sources={
'extraction':'reconstruction/shared/extraction/embedded-mcu-01/REPORT.md',
'extraction_registry':'reconstruction/shared/extraction/embedded-mcu-01/manifest.json',
'fpga_id':'evidence/recovery/2026-10-27/fpga-identification/assessment.json',
'fpga_images':'evidence/recovery/2026-10-27/fpga-identification/manifest.json',
'photos':'evidence/recovery/2026-10-27/nimh-fpga-decode-01/photo-correlations.json',
'photo_hashes':'evidence/recovery/2026-10-27/nimh-fpga-decode-01/photos/manifest.json',
'decode':'evidence/recovery/2026-10-27/nimh-fpga-decode-01/REPORT.md',
'connectivity':'evidence/recovery/2026-10-27/nimh-fpga-connectivity-02/REPORT.md',
'functional':'evidence/recovery/2026-10-27/nimh-functional-03/REPORT.md',
'blocks':'evidence/recovery/2026-10-27/nimh-functional-03/block-assessment.json',
'avb':'evidence/recovery/2026-10-27/nimh-functional-03/avb-register-map.json',
'clocks':'evidence/recovery/2026-10-27/nimh-functional-03/clock-domains.json',
'command':'reconstruction/artifacts/mixer-13731/nimh-stm32-dice/analysis/command-paths.md',
'rx':'reconstruction/artifacts/mixer-13731/nimh-stm32-dice/analysis/receive-path.md',
'panel':'evidence/recovery/2026-10-27/lpc-system-control/REPORT.md',
'fader':'evidence/recovery/2026-10-27/efm32-faders/REPORT.md',
'protocol':'evidence/recovery/2026-10-27/efm32-update-protocol/PROTOCOL.md',
'panel_protocol':'evidence/recovery/2026-10-27/efm-reconstruction/panel/PANEL_PROTOCOL.md',
'readback':'evidence/recovery/2026-10-27/efm-reconstruction/review/READBACK_REVIEW.md',
'dsp':'evidence/recovery/2026-10-27/c674x-dsp/REPORT.md',
'dsp_process':'evidence/recovery/2026-10-27/c674x-dsp/extraction-01/process-map.json',
'dice':'uc-library/validation/dice-image/REPORT.md'}
for key,p in sources.items():assert (R/p).is_file(),(key,p)
# Independently distinguish gzip object identity from decoded configuration identity.
fm=json.loads((R/sources['fpga_images']).read_text());images=fm['inputs'][0]['images'];identity=[]
for image in images:
 comp={'nimh_fpga_code':'nimh-fpga-dice','noaa_fpga_code':'noaa-fpga-dice','esa_fpga_code':'esa-fpga-dice'}[image['demangled']]
 p=R/'reconstruction/artifacts/mixer-13731'/comp/'firmware/mixer-analysis'/ (image['mangled']+'.bin')
 b=p.read_bytes();raw=gzip.decompress(b)
 assert hashlib.sha256(b).hexdigest()==image['gzip_sha256']
 assert hashlib.sha256(raw).hexdigest()==image['raw_sha256']
 identity.append(dict(component=comp,payload=str(p.relative_to(R)),gzip_sha256=image['gzip_sha256'],raw_filename=image['raw_filename'],raw_sha256=image['raw_sha256'],raw_bytes=len(raw)))
changed=[]
def l(label,target,parent):
 target=Path(target);assert target.exists(),target
 return '['+label+'](<'+os.path.relpath(target,parent)+'>)'
def save(p,text):
 if p.exists():
  b=E/'before'/p.relative_to(R);b.parent.mkdir(parents=True,exist_ok=True);assert not b.exists();b.write_bytes(p.read_bytes())
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text);changed.append(p)
def page(component,title,body,keys):
 p=H/component/'README.md';old=p.read_text() if p.exists() else ''
 tail=''
 if '## Software extraction points' in old:tail='\n## Software extraction points'+old.split('## Software extraction points',1)[1].split('[How discoveries',1)[0]
 text='# '+title+'\n\nCanonical hardware knowledge independent of the software release used to observe it.\n\n'+body.strip()+'\n\n## Sources and detailed evidence\n\n'
 for key in keys:text+='- '+l(key.replace('_',' ').capitalize(),R/sources[key],p.parent)+'\n'
 text+=tail+'\n'+l('System architecture and discovery workflow',H/'README.md',p.parent)+'\n'
 save(p,text)
page('nimh-card','NIMH AVB card: system architecture','''
## Physical inventory

These are recorded photograph observations, bound by the photo manifest, not newly measured continuity.

| Part / marking | Role / evidence | Unresolved |
|---|---|---|
| `400-XMEN-NIMH-C` / `400-XMEN-NIMH` | Board markings across the photographed material | Exact revision equivalence and serial applicability |
| STM32F103ZET6 | Cortex-M3 control MCU | Full package-pin/connector mapping |
| XC6SLX45 CSG324 `-2C` | Spartan-6 FPGA; IDCODE `0x04008093` corroborates die family | IDCODE alone does not encode package/speed |
| ISSI IS66WV51216DBLL-55TLI | 512K × 16 parallel pseudo-SRAM | MCU/FPGA sharing and address/data permutation |
| Marvell 88E6240, Pulse magnetics, RJ45 | Ethernet switch/connector group | Port routing, management nets and straps |
| LSI L-FW842-07, two FireWire connectors | FireWire-side group; PHY role inferred from topology/device family | Link-side signals and FPGA balls |
| Long board-to-board connector | Host/control/audio interface candidate | Pinout, direction and signal names |

Separate resonator/oscillator components are visible near the switch and LSI device; frequencies and FPGA clock-input assignments are not established from adjacency.

## Functional partition

STM32 plus FPGA implements the logical DICE role. Firmware-backed register interfaces support AVB, Ethernet/PTP, audio routing, serial audio and clock/HPLL control. This does not establish an identical integrated-DICE implementation. Main mixer dynamics/effects execute on the OMAP DSP; NOAA-subsystem GEQ takes a separate control/routing path.

```mermaid
flowchart LR
    HOST[Linux host] -->|SPI command traffic| MCU[STM32 control]
    MCU -->|16-bit FSMC; physical balls unresolved| FPGA[Spartan-6 fabric]
    FPGA -. candidate RGMII .-> SW[Marvell Ethernet switch]
    SW --> ETH[RJ45 and magnetics]
    FPGA -. ownership and wiring unresolved .-> RAM[ISSI parallel memory]
    FPGA -. link-side wiring unresolved .-> PHY[LSI FireWire group]
    HOST -->|shared-memory control| DSP[OMAP C674x audio engine]
    DSP -. software-visible TDM routes .-> FPGA
```

Dashed connections show hypotheses or software-visible boundaries, not a measured electrical schematic.

## Recovered interface map

Software observations below are from SHA-bound mixer-13731 NIMH firmware. Addresses describe its programmed interface, not a claim of a universal DICE map.

| Interface | Observed address / structure | Evidence scope |
|---|---|---|
| External control | `0x6000xxxx` | Native loads/stores and static FSMC setup |
| External tables/buffers | `0x6400xxxx` | Native register/table references |
| AVB listeners | `0x60000c00 + id*0x20`, id 0..3 | Four addressable banks; not four active streams |
| AVB talkers | `0x60001200 + id*0x20`, id 0..3 | Four addressable banks; capacity/activity unresolved |
| Ethernet/RTC | `0x60004000` | MAC config `+0x300`; RTC snapshot `+0x0c/+0x10/+0x14` |
| PTP | Same base, RX `+0x80`, TX `+0x100` | Relative register layout corroborated by DICE manuals |
| Router | Setup `0x60005000`; table `0x64004000` | Code-backed reads and diagnostic field extraction |
| Clock selection | `0x60005104`, `0x60005108`, `0x60005110` | Router clock, WC/EC and HPLL selectors |
| Mixer coefficient | `0x60005204` | 216 bounded native register-write replay cases |
| Serial audio / InS | `0x60005640`, `0x60005644`, `0x60005648` | Code-backed indexed clock register table |
| HPLL | Initial pointer `0x60006000` | Reference/divider/bandwidth/phase/lock diagnostics |

## Patterns and corrections

Read peripheral-register accesses separately from diagnostics: `PTP HW STATUS` reads a software statistics array at `0x2000dd20`, not a hardware register block. A DICE ETH manual absolute-base typo is not copied into the NIMH map; verified relative offsets and native NIMH addresses take precedence.

The early photo study left FSMC use unknown. Later static startup/code establishes configured 16-bit FSMC use, while physical FPGA ball mapping remains unknown. This is an evidence-backed refinement, not proof supplied by photographs alone.

## Open questions

Confirm board revisions, connector/FSMC balls, memory ownership, RGMII lane order and DDR phases. Join register decoder interfaces to exact FPGA cell cones. Recover clock/packet/audio behavior and measure timing only under separately authorized hardware testing.
''',['photos','photo_hashes','functional','blocks','avb','clocks','dsp'])
page('nimh-stm32-dice','NIMH STM32: control, memory and external bus','''
## Architecture

Photograph records identify STM32F103ZET6, Cortex-M3, 512 KiB flash and 64 KiB SRAM. The board uses the MCU with FPGA-backed peripherals. Software provides an eCos/TCAT runtime and customer command/control code. The part's capabilities and a firmware-configured interface are distinct from a measured board pinout.

## Memory and boot observations

| Item | Observed range/value | Scope |
|---|---|---|
| Initial stack / reset | `0x20010000` / pointer `0x08004511` | Raw NIMH vector/header |
| Image | `[0x08000000,0x08034f4c)` | 216,908-byte export, not complete flash dump |
| Runtime vectors | VTOR `0x20000000`; entries 2..74 written | Bounded reset replay; slots 0/1 untouched in tested segment |
| Initialized data | Flash `[0x080340e8,0x08034f4c)` → RAM `[0x20000400,0x20001264)` | 3,684 bytes copied |
| BSS | `[0x20001268,0x2000e414)` | 53,676 bytes cleared |
| Unclassified gap | `[0x20001264,0x20001268)` | Not labeled heap/stack |
| Above BSS to initial SP | 7,148 bytes | Not established free memory |

Flash words after the first SP/reset entries are metadata, not a conventional full flash vector table. Reset execution stops before complete boot; early hardware init and SVC are modeled boundaries in that replay.

## External bus and peripheral patterns

Static hardware-init code at `0x08004a44` configures FSMC with BCR1/BCR2 `0x81915` and BCR4 `0x1011`; the width field selects 16 bits. Real code references use control `0x6000xxxx` and table/buffer `0x6400xxxx` regions. Initialized RAM pointer `0x20000e08` holds HPLL base `0x60006000`; it is an initial value, not an immutable runtime guarantee. Exact address/data/control pin connections and memory sharing remain unknown.

The SPI1 receive setup programs data register `0x4001300c`, DMA1 channel 2, control `0xaf`, count 1,024 and buffer `0x2000cd14`. Parser `0x08000aa4` consumes modulo-1024 DMA position, recognizes frames and selects queues. Ordinary queue at `0x2000b480` has eight 256-byte slots with seven committed packets usable; other queues serve command `0x15` and commands above `0x3f`.

The replay covers 20 framing/queue cases, three alternate-queue cases and four fragmented commands through native dispatch/release. GPIO, interrupt delivery, scheduling and physical DMA arrivals remain modeled. A whole unseen DMA revolution is not detectable from the modulo index alone.

## Software-derived interface findings

- Host rate/link command `0x11`, AVB clock-source `0x28`, routes `0x16`; ACK proves acceptance, not clock lock or completed topology changes.
- Producer state at `0x20002b90` wakes a deferred worker; 12 tested inactive-link consumer cases copy pending rate/link state and clear the request.
- Runtime family is eCos/TCAT; 124 CLI records and 24 SDK paths are analysis anchors. Application `1.5.5.0` and SDK `1.0.0.0 local beta` identify the sampled software, not MCU hardware or exact eCos revision.
- Mixer coefficient callback writes `0x60005204`; index roles remain neutral where manual labels conflict.

## Open questions

Exact eCos vendor source/configuration, complete initialization and callback flow, clock completion, external bus timing, overrun/concurrency behavior and physical pin assignments remain unresolved. No embedded original C++ identities, production reconstruction, ABI compatibility or hardware equivalence is claimed.
''',['extraction','command','rx','functional','blocks'])
page('nimh-fpga-dice','NIMH Spartan-6: fabric, interfaces and recovery limits','''
## Physical and configuration identity

The photographed FPGA is XC6SLX45 CSG324 `-2C`; IDCODE `0x04008093` independently corroborates XC6SLX45, but not package or speed grade. The NIMH gzip object is 450,319 bytes, SHA-256 `0a6ff55b76117590464f2f32708b255c8db99406f4dac4490ae563e260513c20`. Its decompressed `xmen_nimh_avb_top.bin` is 1,485,512 bytes, SHA-256 `945b2c3a0f74cd39825ec361da680c92303f20ac7f7a98756b7a829216ef9dbb`. These two hashes identify successive representations, not conflicting firmware. Both were independently checked during consolidation.

The stream uses 16-bit big-endian Spartan-6 packet words, sync at raw offset `0x10`, and direct FDRI writes. No MFWR/MFW compression or CTL DEC encryption is indicated. Gzip CRC/size checks pass; FPGA configuration CRC is a separate unproven check.

## Configuration, connectivity and logic findings

| Layer | Established result | Important limit |
|---|---|---|
| Frames | 9,072 main, 128 BRAM, one I/O frame; 11,856,256 storage bits | Frame-byte audit is not independent semantic validation |
| Decode | 10,335,005 unique bits, 87.1692% | Includes zeros/defaults; not utilization or algorithm coverage |
| Unknown bits | 1,521,251 total; two set bits | HCLK frames 8491/8492 bits 513/512 remain unnamed |
| Connectivity | 695,847 canonical wires; 575,677 directed edges | Routing abstraction, not electrical timing |
| Primitive bindings | 360,748/360,748 mapped | 2,441 distinct primitive-input nets lack modeled source |
| Input binding sources | 255,527/257,975 have unique abstract source (99.0511%) | Not functional-equivalence percentage |
| Package | 218 user-I/O paths; 65 configured output drivers | Configured does not prove runtime drive |
| Partial equations | 43,000 equations across 6,254 slice instances; 130 output/tristate roots | Cone/boundary counts, not independent algorithms |

Recovered equation categories include 18,361 LUTs, 18,073 FF equations, 1,637 mux equations, 1,272 XOR equations and explicit gaps. Modeled behavior includes LUT truth tables, register controls, latches and carry equations. BRAM, DSP, serializers, complex input-register and clock-generator behavior retain boundaries; F7/F8 polarity, SRL and dedicated modes require further independent semantics.

Eight structural increment counters have widths 11,11,11,10,9,8,8,8. All 8,448 word states were checked for the increment relation. Width alone does not assign RTC/PTP/audio roles. A bounded raw-to-simplified audit compared 104,320 values and 1,156,928 register-transition tuples; it validates the rewrite domain, not FPGA silicon behavior. Final Yosys checking establishes parsing/hierarchy, not full synthesis or timing closure.

## Interface discoveries

STM32 code supports a 16-bit FSMC control region and AVB/listener/talker, MAC/RTC/PTP, router, clock, HPLL and InS register blocks. Exact register-to-cell-cone assignment remains open; see the card interface map.

Candidate DDR RX lanes are C18,D18,E18,F18,G18; candidate rank2-clock TX/clock lanes are E16,F16,G16,H16,J16,K16. Widths, I/O structure, switch photos and MCU MAC code support an RGMII grouping hypothesis. Individual RXD/TXD order, control/clock assignment, switch port and DDR phases are unverified. No exact original board-net assignments have been admitted.

## Patterns and historical corrections

The initial identification report predates decode, connectivity and partial-logic work; its 'logic not decoded' status is historical. Storage coverage, routed-source coverage and bounded functional rewrite checks have different denominators and must remain separate. The earlier SPI_BUSWIDTH database issue was corrected by using MODE-register semantics; a reboot setting is not evidence of the active programming transport.

## Open questions

Resolve the two HCLK bits and missing primitive semantics, confirm physical FPGA/FSMC/RGMII/serial-audio pin assignments, bind decoder cones to named registers, and recover packet/timestamp/audio behavior. Complete HDL hierarchy, original signal names, timing closure, full equivalence and hardware interoperability are not recovered.
''',['fpga_id','fpga_images','photos','decode','connectivity','functional','blocks'])
page('nimh-marvell','NIMH Marvell switch and Ethernet boundary','''
## Physical findings

Photograph records identify Marvell **88E6240**, nearby Pulse magnetics and RJ45. This establishes the visible Ethernet-facing group, not the FPGA-connected port number, strap configuration or exact management wiring.

## Software and FPGA observations

STM32 Ethernet initialization references base `0x60004000`, MAC configuration `+0x300`, PTP RX `+0x80/+0x84/+0x88`, TX status `+0x104` and system configuration `+0x288`. RTC snapshots use `+0x0c/+0x10/+0x14`. These are FPGA-side software-visible MAC/PTP interfaces; do not call them proven Marvell internal register addresses.

The FPGA has five candidate DDR receive lanes at C18..G18 and six candidate TX/clock lanes at E16,F16,G16,H16,J16,K16. RGMII grouping is a strong structural hypothesis, not confirmed signal order or port wiring. CLI/source records contain marvell and mdio groups; their presence alone does not establish completed switch configuration recovery.

## Architectural pattern

Separate the external switch/PHY management plane, FPGA MAC/PTP datapath and host/STM32 control plane. A named register block or status string does not prove end-to-end Ethernet/AVB conformance.

## Open questions

Switch port mapping, MDC/MDIO continuity, straps, initialization sequence, VLAN/forwarding configuration, timestamp ingress/egress boundaries and live link behavior remain unresolved. No standalone switch configuration artifact or hardware capture has been validated by this task.
''',['photos','photo_hashes','functional','avb','command'])
page('nimh-memory','NIMH external parallel memory','''
## Physical findings

The photo record identifies **ISSI IS66WV51216DBLL-55TLI**, a 512K × 16 parallel pseudo-SRAM, adjacent to the FPGA. Device-interface semantics identify address A[18:0], data DQ[15:0] and memory-control signal classes; they do not assign board nets.

## Software observations and pattern

STM32 startup configures a 16-bit FSMC interface and uses `0x6000xxxx` control and `0x6400xxxx` table/buffer regions. This strengthens a parallel-bus architecture but does not establish that every external access targets this memory chip. Keep FPGA register windows separate from physical SRAM capacity and chip selection.

## Open questions

Address/data permutation, byte enables, chip selects, read/write timing, arbitration and MCU/FPGA ownership/sharing remain unmeasured. Physical adjacency does not prove exclusive ownership.
''',['photos','functional'])
page('nimh-firewire','NIMH FireWire-side hardware','''
## Physical findings

Two FireWire connectors and LSI **L-FW842-07** are visible in the photo record, with nearby protection/filter groups. A FireWire PHY/interface role follows connector topology and device-family identification; individual FPGA-link bus signals and balls are not established.

## Software observations and pattern

The NOAA-family host interface includes FireWire/AVB routing and clock-control paths. That application capability is separate from proof of fitted interfaces or active PHY configuration on a specific unit. NOAA/ESA/NIMH bundle selection must not be interpreted as three simultaneously installed FPGA chips.

## Open questions

PHY/link wiring, clock sources/frequencies, reset/control nets, active host route topology and exact electrical behavior remain unresolved.
''',['photos','fpga_id','dsp'])
page('host','Linux host processor and control boundaries','''
## Mixer architecture

Static loader and processing-location evidence identifies an **OMAP-L138 ARM9 + C674x DSP** architecture for the inspected mixer. Linux ARM configures DSP processors and coefficients, boots embedded DSP payloads and exchanges shared-memory messages. This is stronger than the prior user-only OMAP lead; it does not establish every surface/mixer board uses the same processor.

The DSP link maps physical `0x8001c000`, length `0x4000`. `OMAPTargetHandler` and `Presonus::Link::Messenger` connect host property messages to DSP consumers. Main mixing, channel EQ, gate, compressor, limiter, reverb and delay execute on DSP callbacks; GEQ parameters and insertion take the separate NOAA subsystem path.

## Host-to-peripheral partition

The mixer emits card command/control packets over SPI; acceptance ACKs are separate from clock/audio completion. The surface host uses panel UART `/dev/ttyS1`; runtime codec emits ASCII-hex fields followed by opcode, normally 115200 with optional 230400 in the source port. Its panel firmware update path invokes outer LPC ISP, not direct nested EFM flash access.

Host symbols identify application interfaces, not embedded raw-image functions or fitted boards. Shared fader-related classes in mixer ELF do not establish the presence of motorized fader hardware.

## Open questions

Exact processor package/board revisions, surface host identity, connector maps, active stream topology and scheduling/latency remain unresolved here. No live host/peripheral communication or hardware test was performed.
''',['dsp','dsp_process','command','protocol','fader'])
page('dsp','OMAP C674x DSP: audio processing partition','''
## Loader, memory and control

The inspected mixer embeds ten DSP load payloads totaling **723,936 bytes**, including **161,632 bytes** in three executable objects. Original ARM-side data symbols include `_text`, `_fasttext`, `_text__c_int00`, `_const`, `_cinit`, `_pinit`, `_switch`, `_far`, `_mark` and `_data`.

| Runtime region | Observation |
|---|---|
| `0x80000000` | 128-byte startup entry |
| `0xc7087800` | 137,600-byte `_text` |
| `0x11818600` | 23,904-byte `_fasttext` |
| `0xc7000000` | 554,520-byte loaded `_far` data, not code |
| `0xc70c3960` | 1,140-byte initialization table; 64 parsed records |
| `0x8001c000`, size `0x4000` | ARM/DSP shared-memory link |

`bootDSP` copies section-bound embedded payloads. `mixer_dsp.out` is a manager argument; it does not prove an external file was read. The synthetic C6000 load ELF is analysis scaffolding, not an original `.out` or a flash image.

## Processing discoveries

| Role | Target ID | DSP audio callback |
|---|---:|---|
| Main mixing engine | 30 | `0xc708dfa0` |
| Channel EQ | 12 | `0x1181cda8` |
| Gate | 5 | `0xc709b192` |
| Compressor | 6 | `0xc709fb32` |
| Limiter | 4 | `0x1181db0a` |
| Reverb | 22 | `0xc7089a20` |
| Delay | 23 | `0xc7095978` |

These analyst role labels bind host target IDs, DSP type-accessor values, process tables, property consumers and executable arithmetic. They are not recovered original DSP class/function names. Main-engine floating-point summation and child callback calls establish actual processing paths, not merely parameter setters.

Host messages include `comp`, `gate`, `lim `, `iir4`, `mbqd`, `mprm` and `mpro`; endian presentation is documented in the source report. Compressor, gate and EQ callbacks reach fast arithmetic kernels. Seven expected process bindings passed static assertions; no DSP code was executed.

## Offload boundary

NOAA GEQ sends a 36-byte SysEx frame: command `0x1d`, selectors and 31 seven-bit band values, then configures a TDM GEQ insert or bypass. This establishes GEQ control/routing offload to the card subsystem, not the exact CPU/FPGA location of GEQ arithmetic. Do not move the independently identified OMAP dynamics/effects into the card model.

## Open questions

Complete kernel equations and modes, model/sample-rate-specific graph, DMA/audio serial pin mapping, original DSP declarations, runtime latency and exact GEQ execution hardware remain unresolved. Disassembly coverage and byte extraction are not semantic or timing validation.
''',['dsp','dsp_process'])
page('panel','LPC panel/system controller','''
## Identification and images

All three inspected outer panel arrays use initial SP `0x10002000` and LPC-family SYSCON `0x40048000`, IOCON `0x40044000` and USART `0x40008000`. Their sizes fit the user-identified LPC1317 and its SRAM0/flash map. Exact suffix/revision remains unproved by bytes alone; keep surface, rack and additional variants distinct.

| Source role | Host symbol | Bytes | Reset pointer |
|---|---|---:|---|
| Surface | `panel_surface_code` | 53,364 | `0x127` |
| Rack mixer | `xrackpanel_code` | 28,308 | `0x165` |
| Additional mixer-carried variant | `xmenpanel_code` | 58,072 | `0x11f` |

The additional image's presence does not prove it runs on the fitted rack panel. Initial eight-word checksum sums are nonzero and word `0x1c` is zero; no updater transformation or checksum repair is inferred. Arrays are exact update payloads, not complete certified flash dumps.

## Host and fader boundaries

Surface host UART `/dev/ttyS1` carries runtime ASCII-hex/opcode messages. Outer-panel replacement uses LPC ISP; `LPCProgrammer::open` includes `unlockFlash`, so it is not a read-only discovery routine. Host code references GPIO102/110 sequencing; physical reset/boot wiring remains unverified.

The surface panel contains a separate EFM32 application at outer offset `0x9e40`, length `0x2f70`. Normal-return startup calls updater `0x80d8` before its main loop. Panel I2C wrapper uses base `0x40000000`; address helper emits `(address<<1)|direction`. Logical target addresses are **0x61,0x60,0x69,0x68,0x6f**, not raw eight-bit write addresses or a verified board count.

Update transfer sends a 14-byte header and then fixed nested image bytes. Header includes version `0x1b`, LE32 length `0x2f70`, CRC-32 `0x2a9026dc`, and modulo-255 checks. Response helper returns only byte3 of a separate six-byte receive. A terminal I2C error can still yield the wrapper's nonzero completion return; normal return does not prove successful programming.

## Patterns and corrected findings

The earlier fader extraction retained ambiguous raw target bytes. Later address-helper analysis establishes seven-bit address values and explicit TX/RX address-byte formation. This updates the protocol knowledge without proving physical wiring. Header CRC/checksum models and nested-app behavioral checks are different proof domains from outer updater execution.

## Open questions

Confirm exact panel MCU/board revisions, physical target selection, controls and host reset wiring. ADC/buttons/encoders/fader/touch/LED maps and outer-updater timing/error behavior remain incomplete. No bootloader-read path follows from normal UART/I2C receive capability.
''',['panel','panel_protocol','protocol','fader','readback'])
page('faderboard','EFM32 faderboard: application, protocol and boot boundary','''
## Physical and memory identification

Photo evidence appears to show **EFM32ZG222**; the full flash-size suffix is unreadable. Cortex-M0+ instruction/vector and EFM32ZG peripheral-map evidence corroborate the family, not exact flash capacity.

| Region / peripheral | Observation |
|---|---|
| Application | `[0x1000,0x3f70)`, 12,144 bytes |
| Missing boot region | `[0,0x1000)` absent from the application export |
| Initial stack / reset | `0x200008d0` / `0x11dd` |
| Vector relocation | VTOR set to `0x1000` |
| GPIO / I2C0 | `0x40006000` / `0x4000a000` |
| TIMER0 / TIMER1 | `0x40010000` / `0x40010400` |
| ADC0 / CMU / MSC | `0x40002000` / `0x400c8000` / `0x400c0000` |

Exact application hash is `b87a39cea8ff234c0cca785a7c5433e4ff729d365b56fca05b3023caa3aa53b6`; it is nested in outer surface panel bytes at `+0x9e40`. Five logical I2C targets and a four-channel wildcard selector are software observations, not proof of physical board/fader count. The same payload was absent from the inspected primary mixer and 17 mixer archive members; shared fader-related host classes do not negate that bounded result.

## Receive and command model

Normal path: I2C IRQ `0x1d34` → receive FSM `0x1518` → wrapper `0x13ac` → checksum validation `0x2a84` → dispatcher `0x2230`. Packet is `[destination,command,length,payload...,a,b]`. Normal context is `0x200001d8`, packet RAM `0x20000144`, bank zero. Destination high nibble matches board ID or broadcast `0xf`; low nibble selects a channel, with `0xf` selecting `[0,4)`. Selectors 4..14 are not rejected before helpers; malformed-input behavior is not validated.

| Commands (low seven bits) | Reviewed behavior |
|---|---|
| `0x11` | Control/reinitialization; read bit ignored |
| `0x12..0x1f`, `0x27` | Default return in reviewed application table |
| `0x20,0x21,0x22,0x23,0x28` | Fixed RAM-context parameter reads/writes |
| `0x24` | Sets control flag `0x200001ce`; read bit ignored |
| `0x25` / query `0xa5` | Fixed flash version byte at `0x3e28`, value `0x1b` |
| `0x26` | Flag `0x20000378` → persistence-like helper → AIRCR reset request |
| `0x29,0x2a` | Low-byte reads of fixed RAM words; write no-op |

Query bit `0x80` is not a universal read-only modifier: `0x91`, `0xa4`, `0xa6` retain control side effects. No reviewed normal-table command takes a caller-selected flash address and length. That does not prove all indirect/malformed paths or the absent bootloader lack read access.

## Update and validation findings

Panel query bytes are `00 a5 00 a5 4b`; control bytes `00 26 00 26 4c`. Observed update header is `00 27 09 1b 70 2f 00 00 dc 26 90 2a a8 fb`. CRC uses reflected `0xedb88320`, initial all ones and final complement. Checks use `a=(a+x)%255`, `b=(b+a)%255`. These bytes describe offline findings, not commands executed against hardware.

Nested-app checks include 5,632 checksum and 8,192 command25 full-packet native/Thumb comparisons; 17 portable undersized-buffer checks have their own scope. Other table handlers, peripheral behavior and the entire outer updater are not established by those tests.

## Bootloader and open questions

The original bootloader is **not acquired**. No demonstrated arbitrary flash/bootloader dump command exists in the inspected evidence. Command `0x27` is default-return in the normal app; its actual update receiver is absent. Reset landing and `0xfe` status meaning remain unresolved. Stock Silicon Labs AN0003 is UART/XMODEM with a `0x800` application boundary; it is not identified as the PreSonus I2C loader with this observed `0x1000` application base.

Exact part suffix, motor-driver wiring, ADC position/touch origin, timer/PWM pin assignment, persistence semantics, physical board count and full boot/flash behavior remain open. No hardware read, reset, erase, programming or debug unlock was performed.
''',['fader','protocol','panel_protocol','readback'])
page('dice3','Surface integrated DICE III processor','''
## Architecture and boot

Local hardware/memory-map manuals identify an ARM926/ARM9EJ-S core and 320 KiB internal SRAM. This is integrated DICE III firmware, not Cortex-M, STM32 or a Linux ARM ELF. The raw image is 230,512 bytes, SHA-256 `0468d888f3d615e70065f5d535b9eadac7f8bf67185b53cc19c2cb7986c1d946`. The separate `components/dice3-surface-bin` has four trailing zeros and is a distinct artifact.

| ROM SPI header field | Observed value |
|---|---|
| Magic / family | `TCAT` / 3 |
| Flags | `0x31`: divider field1, PLL enabled, checksum enabled, fast-read disabled |
| PLL multiplier / pre-divider | 100 / 3 |
| Load address | `0x200` |
| Payload | 57,624 words, 230,496 bytes |
| SPI baud divider | 2 |

Entry `0x200` branches to `0x240`; runtime address = image file offset + `0x1f0`. Startup configures ARM modes/banked stacks and copies exception vectors to low memory. This is the 16-byte ROM header, not BOOT2 magic `0x20120710`.

## Runtime and register observations

The image contains 105 tagged CLI descriptors with 105 aligned ARM callbacks. Labels include mixer gain/configuration and six DAL callbacks; they are registration labels, not original C++ names or exact extents. Bounded mixer callbacks address coefficient register `0xc4000204` and configuration `0xc4000200`. Shared architectural roles with NIMH do not establish identical addresses, binaries or peripheral semantics.

SDK banner `1.0.0.0 local beta`, application `0.0.0.6`, target `Surface-AVB/DICE Option Card` and December 2015 build/date strings identify software provenance leads. They do not establish exact eCos source revision.

## Open questions and validation limits

ROM checksum validity is unresolved: tested MSB-first interpretations did not yield the documented zero residue. Bytes were not changed to force a match. No firmware execution, complete boot, physical peripheral behavior, original internal function symbols or cross-platform binary equivalence is established. Map subsystem behavior using local architecture manuals rather than direct CS18/RM firmware mapping.
''',['dice','extraction'])
# Variant-specific hardware facts from the exact decoded packet registry.
for family in ['noaa','esa']:
 im=next(x for x in images if x['demangled']==family+'_fpga_code')
 page(family+'-fpga-dice',family.upper()+' FPGA variant: identified configuration target',f'''
## Established configuration facts

The mixer carries a variant-specific gzip payload `{im['raw_filename']}` with decompressed size {im['raw_size']:,} bytes. Its recorded IDCODE is `0x04008093`, identifying Spartan-6 XC6SLX45. No package/speed-grade claim for this variant follows from the NIMH board photographs.

The stream uses 16-bit big-endian packet words, sync at raw offset `0x10`, and clear CTL DEC bits in the inspected writes. Gzip CRC/ISIZE and complete packet accounting pass; FPGA configuration CRC is not recomputed.

'''+('NOAA `storm_top.bin` uses repeated-frame compression: 2,162 MFWR register writes and 57 MFW commands. Expand repeated frames before frame-address comparison.\n\n' if family=='noaa' else 'ESA `xmen_esa_top.bin` uses direct FDRI writes without observed MFWR/MFW compression.\n\n')+'''
## Architecture pattern and open questions

Host bundle selection distinguishes NIMH, ESA and NOAA variants; bundled images do not prove multiple fitted FPGA chips or the image currently programmed. NIMH decode/connectivity/functional results must not be generalized to this variant. Physical board/part mapping, package, pinout, active feature set, logic and interface behavior remain unresolved here.
''',['fpga_id','fpga_images','extraction'])
 page(family+'-stm32-dice',family.upper()+' MCU firmware family: hardware constraints','''
## Established observations

This separate raw MCU image starts with SP `0x20010000` and an odd reset pointer in STM32 flash range `0x08000000`. Strings include `STM32 Internal Flash`, module banners and STM32F1 RCC `0x40021000`, flash `0x40022000` and VTOR `0xe000ed08` references. Thumb startup inspection supports the STM32 family. Exact board/part mapping is not established from the NIMH photograph.

## Architecture pattern

Keep card MCU and FPGA payloads separate. Use vector/memory/peripheral evidence to constrain analysis before interpreting names. Public SDK/runtime matches and NIMH command paths are comparison leads, not recovered behavior for this image. NOAA GEQ host-side control/routing is established at subsystem level; its arithmetic execution site remains unknown.

## Open questions

Confirm variant board and MCU identity, runtime memory layout and source lineage, target selection and transport, physical interfaces and behavior for this exact image. No new hardware or semantic replay is established by extraction alone.
''',['extraction','extraction_registry','fpga_id','dsp'])
# Human entry now explains what is physically known rather than only listing folders.
index=H/'README.md';old=index.read_text();workflow=old[old.index('## Updating the hardware model'):]
intro='''# Hardware architecture and discovered knowledge

This is the canonical physical-system model. A software version is an evidence source,
not a hardware identity. Read a component here before extraction; reconcile new software
facts back into it with source hashes and explicit validation scope.

## System partition

- **Mixer host / DSP:** OMAP-L138 ARM9 runs Linux control; C674x executes main mixing,
  dynamics, channel EQ and effects. Shared memory links host and DSP.
- **NIMH AVB card:** STM32F103ZET6 plus XC6SLX45, external ISSI memory, Marvell switch
  and LSI FireWire-side group. STM32 code exposes FPGA-backed routing, AVB/PTP and clock interfaces.
- **Surface:** integrated ARM926 DICE III firmware is distinct from the LPC panel MCU.
  The panel contains and distributes a separate EFM32 fader application over I2C.
- **Variants:** NOAA/ESA images establish separate MCU/FPGA software families; physical
  board mapping and package assumptions must not be copied from NIMH without evidence.

## Component knowledge

| Component | What is established | Main unknown |
|---|---|---|
'''
summary={'nimh-card':('Board inventory and joint MCU/FPGA role','Physical interconnect and revision applicability'),'nimh-stm32-dice':('Memory, SPI/DMA queues, FSMC configuration and register accesses','Physical buses, completion and concurrency'),'nimh-fpga-dice':('Frames, partial logic, routing and I/O candidates','Complete primitive semantics, net assignments and timing'),'nimh-marvell':('88E6240 photo identity and candidate Ethernet boundary','Ports, straps and configuration'),'nimh-memory':('ISSI 512K × 16 pseudo-SRAM photo identity','Ownership, pin order and timing'),'nimh-firewire':('LSI marking and connector group','PHY/link net assignments'),'host':('Mixer OMAP-L138 and host control boundaries','Board revisions and surface host identity'),'dsp':('Loaded C674x audio callbacks and shared-memory control','Complete equations, modes and timing'),'panel':('LPC-family images and panel-to-fader I2C protocol','Exact part/revision and physical control mapping'),'faderboard':('EFM32ZG application, command model and absent boot bytes','Original bootloader and motor/ADC pin mapping'),'dice3':('ARM926 boot image, memory and CLI organization','Checksum, full runtime and physical behavior')}
for p in sorted(H.glob('*/README.md')):
 c=p.parent.name;a,b=summary.get(c,('Variant-specific extraction/header observations','Physical board mapping and semantic behavior'))
 intro+='| '+l(c,p,H)+' | '+a+' | '+b+' |\n'
intro+='''
## Evidence levels and corrections

Photograph observations establish visible markings/topology; local manuals establish
reference architecture; native loads/stores and static register arithmetic establish
software-visible interfaces; bounded execution establishes only the modeled/tested domain.
None alone proves fitted wiring, audio equivalence or live timing.

The initial FSMC uncertainty is refined by later configured-bus evidence. The initially
opaque fader target bytes are now seven-bit I2C addresses following the decoded helper.
Fader DSP/boot skeletons have been replaced with the existing DSP and EFM reports.
Earlier FPGA identification/decode statuses are historical checkpoints superseded by
connectivity and partial-functional work, while their unknowns and denominators remain.
The absent PreSonus bootloader is not replaced by stock AN0003 reference sources.

'''
save(index,intro+workflow)
# Append source-bound discovery record, retaining the original skeleton history.
(E/'sources.json').write_text(json.dumps({'sources':{k:{'path':v,'sha256':sha(R/v)} for k,v in sources.items()},'fpga_representation_checks':identity},indent=2)+'\n')
# Check every link in the canonical hardware pages; external URLs remain source-report references.
links=0
for p in changed:
 for url in re.findall(r'\]\(([^\n]*?)\)',p.read_text()):
  url=url.strip('<>')
  if '://' in url or url.startswith('#'):continue
  assert (p.parent/unquote(url.split('#')[0])).exists(),(p,url)
  links+=1
(E/'consolidate.py').write_bytes(Path(__file__).read_bytes())
(E/'validation.json').write_text(json.dumps({'status':'hardware-knowledge-consolidation-checked','time':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_count':len(sources),'hardware_pages':len(changed),'local_links_checked':links,'files':{str(p.relative_to(R)):sha(p) for p in changed},'sources_manifest_sha256':sha(E/'sources.json'),'new_hardware_actions':0,'new_behavioral_validation':False,'original_data_deleted':0},indent=2)+'\n')
print('PASS',len(changed),'hardware pages;',len(sources),'source reports/registries;',links,'local links; three gzip/raw image identities verified')
