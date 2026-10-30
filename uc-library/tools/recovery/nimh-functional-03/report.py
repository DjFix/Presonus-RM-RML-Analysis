"""Generate the phase report from measured coverage and retained proof records."""
from pathlib import Path
from collections import Counter
import json
ROOT=Path('/home/rs/projects/opencs/ai-line-analysis')
B=ROOT/'evidence/recovery/2026-10-27/nimh-functional-03'
load=lambda n:json.loads((B/n).read_text())
c=load('functional-coverage.json');a=load('functional-audit.json');fw=load('stm32-cfg-summary.json')
feedback=load('functional-feedback-components.json');counters=load('binary-counters.json')
io=load('interface-candidates.json');ins=load('ins-register-map.json')
ops=c['equation_ops'];commands=load('commands.json')
yosys=[x for x in commands if x['step']=='yosys'][-1]
assert yosys['returncode']==0
blocks=[
 dict(block='STM32 control bus',status='Established in static startup/code; physical FPGA ball mapping unresolved',
      interfaces=['FSMC 16-bit bank configuration','0x6000xxxx control region','0x6400xxxx table/buffer region'],
      evidence=['firmware-code-windows.json: startup-fsmc','stm32-mmio-accesses.json','stm32-initialized-data-map.json'],
      gaps=['Address/data/chip-select ball assignment; live bus transactions; external SRAM ownership']),
 dict(block='Ethernet MAC / RGMII',status='Register layout is strongly supported; RGMII pin groups are structural candidates',
      interfaces=['Ethernet base 0x60004000; MAC configuration +0x300','Five DDR RX candidate lanes','Six DDR TX/clock candidate lanes'],
      evidence=['stm32-mmio-accesses.json','physical-interface-pins.json','interface-candidates.json','dice-relevant-pages.json: ETH p6'],
      gaps=['Exact lane ordering, switch-port wiring, DDR phase/serialization, RTL MAC datapath attribution']),
 dict(block='RTC / PTP',status='DICE-style relocated register interface strongly supported; complete hardware timestamp path unrecovered',
      interfaces=['RTC at 0x60004000','PTP RX control at +0x80','PTP TX control at +0x100','RTC snapshot words +0x0c/+0x10/+0x14'],
      evidence=['firmware-code-windows.json: rtc-ptp-init, rtc-snapshot','stm32-mmio-accesses.json','dice-relevant-pages.json: ETH pp6-16'],
      gaps=['Exact timestamp counter cells, ingress/egress capture, FIFO bin mapping, filter behavior, 802.1AS compliance']),
 dict(block='AVB talker / listener',status='Firmware-addressed hardware control banks identified; packet engine cell cones unresolved',
      interfaces=['Four listener banks: 0x60000c00 + id*0x20','Four talker banks: 0x60001200 + id*0x20','Enable/mute/channel/stream control fields'],
      evidence=['avb-register-map.json','firmware-code-windows.json: avb-talker-diagnostic, avb-listener-diagnostic'],
      gaps=['Active runtime stream/channel counts, full IEEE1722 packetization/depacketization, scheduler/shaper, timestamp insertion, exact LUT/BRAM assignment']),
 dict(block='Audio router',status='Register and table interface identified by direct loads and named diagnostic formatting; no runtime execution claimed',
      interfaces=['ROUTER1_SETUP: 0x60005000','Route table: 0x64004000','Source/destination channel/device extraction in firmware'],
      evidence=['firmware-register-labels.json','firmware-code-windows.json: router-diagnostic, router-table-loop','dice-relevant-pages.json: Router'],
      gaps=['Exact routing state machine and RAM cells, sample schedule, route-table format completeness, fixed/float conversion']),
 dict(block='Clock / HPLL',status='Control register interface identified; loop behavior and jitter equivalence unverified',
      interfaces=['Clock controller 0x600051xx','HPLL initial pointer 0x60006000','Named reference/divider/bandwidth/phase registers'],
      evidence=['firmware-register-labels.json','stm32-initialized-data-map.json','firmware-code-windows.json: hpll-diagnostic'],
      gaps=['HPLL transfer function, oscillator/VCXO wiring, jitter/lock behavior, two unknown HCLK configuration bits']),
 dict(block='Serial audio / InS',status='Firmware-backed clock control table and driver code identified; external signal order unresolved',
      interfaces=ins['clock_registers'],evidence=['ins-register-map.json','firmware-code-windows.json: ins-clock-control, ins-line-control','dice-relevant-pages.json: InS'],
      gaps=['BCLK/LRCLK/data ball assignment, actual runtime sample format/rates, reconstructed serializers/deserializers']),
]
(B/'block-assessment.json').write_text(json.dumps(blocks,indent=2)+'\n')
table='\n'.join('| '+r['block']+' | '+r['status']+' | '+ '; '.join(r['interfaces'])+' |' for r in blocks)
op_table='\n'.join(f'| {k} | {v:,} |' for k,v in ops.items())
gap_table='\n'.join(f'| {k} | {v:,} |' for k,v in sorted(c['boundary_classes'].items()))
counter_table='\n'.join(f"| {i+1} | {r['width']} | `{r['bits_low_to_high'][0]}` | `{r['clock']}` |" for i,r in enumerate(counters))
feedback_note=('No structural combinational cycles remain after truth-support reduction. Earlier raw replay dependency-order failures are retained as historical attempts; the final audit uses partial-value LUT evaluation to resolve masked dependencies.' if not feedback else 'The remaining structural feedback components require independent interpretation; no timing-dependent latch, pulse-generator or oscillator role is invented.')
text=f'''# NIMH functional logic and hardware block correlation

This phase reconstructs **configuration-derived partial functional logic** from the sealed global netlist on VM101. It also identifies firmware-addressed AVB, Ethernet/PTP, audio-router, clock and HPLL interfaces. The evidence now supports FPGA + STM32 as a joint functional counterpart to the DICE-based surface subsystem. It does **not** establish a complete DICE replacement, original HDL hierarchy, timing equivalence or tested hardware interoperability.

## Inputs and pins

The FPGA input is `xmen_nimh_avb_top.bin`, SHA-256 `945b2c3a0f74cd39825ec361da680c92303f20ac7f7a98756b7a829216ef9dbb`, XC6SLX45/CSG324. Project Combine remains `01bdbb674f784740f977327b2edfe099ebf63ae0`; Spartan-6 database SHA-256 remains `e44e5f9a7075854d653dc1bbb987ed9fe2a63098fcc5aee2a26521cf7f52ad10`. No upstream database or decoder changes are admitted.

The matching MCU object is original mixer-13731 symbol `_ZL13nimh_arm_code`, 216,908 bytes, SHA-256 `b0979352e18a1093051fc6118a47694773cb9240e88087eca03aaa2ffe0f5e17`, extracted from mixer ELF SHA-256 `9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07`. Its original ELF VA is `0x2608d7`, file offset `0x2588d7`. The MCU analysis base is `0x08000000`; reset entry is `0x08004510`. No embedded function has been assigned an invented original C/C++ name or promoted to readiness.

Source, dependency and tool identities are in [pins.json](pins.json). The previous graph's bit and wiring coverage remain separate from this functional phase.

## Functional model

[functional-partial.v](functional-partial.v) is standalone partial Verilog. [functional-equations.jsonl](functional-equations.jsonl) preserves the equation identities. Every unsupported behavior is an explicit boundary input with a name and reason, rather than a fabricated implementation. [verilog-port-map.json](verilog-port-map.json) maps short Verilog identifiers back to physical signal identities and candidate package balls.

The backward model begins at the output and tristate endpoints of all **{c['configured_output_pads']} configured output pads**, or {c['roots']} roots. It reaches **{c['cone_equations']:,} equations** across {c['reconstructed_slice_instances']:,} slice instances, including conservative dependencies of unresolved hard blocks. These are not independent algorithm counts, measured utilization or a functional-equivalence percentage.

| Equation category | Count |
|---|---:|
{op_table}

Modeled behavior includes combinational LUT O5/O6 truth tables, decoded register data/clock/reset/enable/initial controls, active-low latch transparency, carry mux/XOR equations and geometry-backed inter-slice carry connections. Constant/duplicate LUT inputs and inactive truth-table variables are reduced. Configured input polarity and routing inversion are retained. Input-delay paths are functional connectivity only, with no delay or calibration model.

F7/F8 input polarity is retained as an unresolved boundary pending independent physical-input-order evidence. SRL modes retain their configured mode and INIT rather than being misrepresented as static LUTs. BRAM, DSP, serializer, complex input-register and clock-generator behavior remains explicit. Boundary counts are **bit-signal endpoints**, not numbers of physical blocks:

| Boundary class | Endpoints |
|---|---:|
{gap_table}

The complete reasons and dependencies are in [functional-boundaries.json](functional-boundaries.json). Physical equations before simplification, decoded LUT INITs and register controls are retained separately for audit.

## Identified block interfaces

| Block | Evidence strength | Interface |
|---|---|---|
{table}

[block-assessment.json](block-assessment.json) preserves evidence references and remaining gaps for every row. Identification at a register interface does not yet assign that block's exact FPGA LUT/FF/BRAM/DSP cells.

### STM32 bus and initial pointers

Startup at `0x08004a44` configures FSMC bank registers; the retained bounded window includes BCR1/BCR2 values `0x81915` and BCR4 `0x1011`. The width field encodes a 16-bit bus. Firmware performs actual loads/stores into external-memory regions, rather than merely storing addresses in diagnostic strings. The project's photos are consistent with an MCU/FPGA/parallel-memory arrangement, but hidden BGA routes do not prove net assignments or SRAM ownership.

The reset copy loop at `0x08004550`–`0x08004564` copies initial data from `0x080340e8` to `[0x20000400,0x20001264)`. This independently resolves the HPLL base pointer at RAM `0x20000e08` to initial value `0x60006000`. These are initial-state values, not proof that runtime code never changes them. Other address-looking words are explicitly only candidates; the range search also matches non-pointer text/data.

### AVB and PTP

At `0x0801c93e` and `0x0801ca76`, the AVB diagnostic routines bound `id` to 0..3. Their arithmetic computes talker and listener bank bases with stride `0x20`. [avb-register-map.json](avb-register-map.json) retains the exact instructions and decoded fields. This establishes four firmware-addressable instances per direction, not four currently active streams or a live channel count.

The Ethernet initialization window at `0x08019a6c` uses base `0x60004000`, PTP RX offsets `+0x80/+0x84/+0x88`, TX status `+0x104`, and system configuration `+0x288`. The RTC snapshot window reads `+0x0c/+0x10/+0x14`. These relative layouts align with the DICE ETH manual's RTC/PTP organization. The manual's table 16.1 prints a nine-hex-digit absolute base; this report uses the verified relative offsets and NIMH's observed base instead of silently normalizing that typo.

The `PTP HW STATUS` routine at `0x08019260` reads a **software statistics array in STM32 RAM** at `0x2000dd20`. Its title alone is not hardware-register evidence. The independent external-register accesses supply the hardware-interface evidence. Packet parsing, EtherType filters, timestamp capture, FIFO geometry, scheduling and 802.1AS/IEEE1722 conformance have not been recovered or tested end to end.

### RGMII candidate balls

Five enabled DDR input lanes occur at **{', '.join(io['rgmii']['ddr_input_balls'])}**. Six enabled rank2-clock output lanes occur at **{', '.join(io['rgmii']['rank2_output_balls'])}**. The widths, photographed Marvell 88E6240 and firmware MAC/PHY paths make these strong RGMII grouping candidates. The individual RXD/TXD bit order, control/clock assignment, switch port and DDR phases remain unverified. Additional IOCE-enabled outputs are retained separately; they are not all labeled Ethernet.

### Audio and clocks

Firmware reads `ROUTER1_SETUP` at `0x60005000` and iterates route entries from `0x64004000`. Its diagnostic extracts source/destination device and channel fields. Clock diagnostics identify `ROUTER_CLK_SEL` at `0x60005104`, `WC_EC_SEL` at `0x60005108`, `HPLL_CLK_SEL` at `0x60005110`, prescaler and sample-rate counters. The HPLL diagnostic reads named reference, divider, bandwidth, phase and lock/status fields behind `0x60006000`. This establishes control-facing behavior, not the loop transfer function, recovered JetPLL implementation or measured jitter.

The InS routine has code references to the original `diceInS.c` path, indexed clock-register addresses {', '.join('`'+x+'`' for x in ins['clock_registers'])}, and a code-backed argument-packing equation. Serial-audio line routing, runtime formats and BCLK/LRCLK/data pin identities remain open. CS18AI PCM photo annotations remain user leads, not continuity measurements.

## Counter structures

Eight exact self-feedback binary increment recurrences were recognized. Each bit's XOR/carry recurrence and common clock/reset/enable controls are checked structurally; all {sum(1<<r['width'] for r in counters):,} possible word values across these counters are replayed for the increment relation. No counter is assigned an RTC/PTP/audio role solely from its width.

| Counter | Width | Low bit | Clock source boundary |
|---|---:|---|---|
{counter_table}

Full bit order, reset values and controls are in [binary-counters.json](binary-counters.json).

## Validation and limits

All reconstruction and replay ran on VM101 Linux. The bounded rewrite audit compared **{a['compared_output_and_internal_values']:,} output/internal values** and **{a['compared_register_transition_inputs']:,} register transition-input tuples** over {a['abstract_patterns']} deterministic abstract patterns. It also sanity-checked {a['physical_lut_addresses_checked']:,} captured LUT addresses. This validates the raw-to-simplified rewrite in its tested domain; INIT indexing sanity checks do not independently validate silicon bit mapping.

**Complete bounded replay passed: {a['complete_replay_passed']}.** There were {a['skipped_value_comparisons']:,} skipped value comparisons and {a['skipped_transition_comparisons']:,} skipped register-input comparisons. [functional-audit.json](functional-audit.json) gives the complete scope. The graph contains **{len(feedback)} structural combinational feedback components**, with the inventory in [functional-feedback-components.json](functional-feedback-components.json). {feedback_note}

The final full-file Yosys check parses Verilog and checks top-level hierarchy. An independent small probe demonstrates successful lowering of the explicit one-bit inverted-reset control. Earlier whole-design lowering failures/time limits and the inline-reset probe failure are retained under `attempts/` and `experiments/`; full-design synthesis, formal equivalence and timing closure are not claimed. Commands, exit codes and timings are in [commands.json](commands.json).

The MCU pass reached {fw['reset_reachable_instructions']:,} instructions from reset and {fw['pointer_seeded_instructions']:,} in the larger pointer-seeded candidate CFG, with {fw['unresolved_indirect_calls']} unresolved indirect calls. Its {fw['external_accesses']} constant-address external accesses are a lower bound: constants are propagated only within straight-line blocks, joins/calls constrain propagation, and jump tables/runtime callbacks remain incomplete. Linear disassembly and nearby function pointers are retained as candidates, not certified function boundaries or handler registrations.

Configuration storage coverage remains **87.1692%**, with the two set HCLK bits at main frames 8491/8492, bits 513/512, still unnamed. The prior 2,441 rootless primitive-input nets remain a separate routing-model limitation. This phase does not erase either gap or claim that modeled clock connectivity proves the unknown bits harmless.

## Remaining work

1. Confirm FPGA-to-STM32 FSMC address/data/control balls, then map decoded addresses to FPGA read/write decoder cones. This is the key missing bridge between the identified register blocks and exact fabric cells.
2. Model dedicated I/O registers/DDR, F7/F8 polarity, SRLs, BRAM modes and DSP cascades against independent device semantics; resolve the feedback components without assuming their timing behavior.
3. Attribute AVB/PTP packet, FIFO and timestamp paths to those cell cones. Confirm filter constants, scheduler/shaper behavior, clock domains and audio serializer channel/rate formats.
4. Resolve the HCLK bits with independent format/device evidence. Hardware continuity, packet capture, clock/jitter and interoperability tests require devices and separate hardware authorization.

The archive and local mirror include the partial HDL, machine-readable equations and assessments, full unresolved-boundary inventories, firmware windows, source snapshots, tool pins, validation records and hashes. No firmware update, flash/erase, device I/O or C++ readiness promotion was performed.

## Documentation used

- Local DICE ETH guide: module map pp6–16; [source](dependencies/docs/DICE_III_User_Guide_ETH.pdf).
- Local DICE Router guide: routing/table/control model; [source](dependencies/docs/DICE_III_User_Guide_Router.pdf).
- Local DICE InS, ClockController and JetPLL guides: interface and clock comparisons, not proof of an identical NIMH implementation. Their original hashes and selected complete pages are retained in `dependencies/docs-manifest.json` and `dice-relevant-pages.json`.
- Official [AMD UG384](https://docs.amd.com/v/u/en-US/ug384): slice/LUT/register/carry semantics, with downloaded source hash and inspected diagrams retained.
- Official [ST RM0008](https://www.st.com/resource/en/reference_manual/cd00171190-stm32f101-103-105-107-stm32f100-series-armbased-32bit-mcus-stmicroelectronics.pdf): FSMC register interpretation. The initial local download timed out; online official-source evidence is recorded separately and no local PDF hash is invented.
'''
(B/'REPORT.md').write_text(text)
print('Report written; blocks:',len(blocks),'equations:',c['cone_equations'],'feedback components:',len(feedback))
