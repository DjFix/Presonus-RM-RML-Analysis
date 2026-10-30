from pathlib import Path
from datetime import datetime,timezone
import json
ROOT=Path('/home/rs/projects/opencs/ai-line-analysis');B=ROOT/'evidence/recovery/2026-10-27/nimh-bus-04'
load=lambda n:json.loads((B/n).read_text())
c=load('functional-coverage.json');a=load('functional-audit.json');m=load('register-map-coverage.json');v=load('bus-model-audit.json');ram=load('bram-storage-models.json');t=load('transaction-experiment.json')
bank_table='\n'.join('| '+r['bank']+' | '+str(r['candidate_groups'])+' | '+str(r['candidate_cells'])+' | '+str(r['unique_address_groups'])+' |' for r in m['banks'])
capture=load('address-capture.json')['low_bits']
pins='\n'.join('| '+str(i)+' | '+r['ball']+' | `'+r['capture']+'` |' for i,r in enumerate(capture))
tx='\n'.join('| '+r['select']+' | '+str(r['address_valid_level'])+' | `'+r['offset']+'` | '+str(len(r['active_cells']))+' |' for r in t['results'])
text=f'''# NIMH STM32/FSMC and conditional register cones — phase 04

Generated {datetime.now(timezone.utc).isoformat()}. Continued analysis began October 27; this checkpoint completed October 28, 2026 Moscow time. All execution and behavioral checks ran on VM101. No devices were accessed or flashed.

## Result and admission boundary

The bitstream contains a **16-bit synchronous, nonmultiplexed FSMC-shaped bus**, with external clock H3, fourteen captured address lanes, two independently reconstructed 14-bit halfword-address counters. Sixteen bidirectional data pads share one decoded tristate function. This is strong structural correlation with the STM32 firmware's configured 16-bit external bus; electrical continuity and exact STM32 package-pin correspondence are not established.

Recovered **{m['conditional_target_cells']:,} conditional register cells**, {m['conditional_enable_groups']} enable groups, {m['immediate_consumer_edges']:,} immediate sequential/RAM consumer edges and all sixteen bus readback cones. These are exact physical identities under the exported conditions, **not unique named-bank assignments**. The broad scan retained 3,223 address-dependent predicates (enable and next-data), with budget exclusions recorded separately.

**Zero of the eleven named AVB/PTP/audio/control bank regions is admitted as uniquely mapped to a cell cone.** Feedback-based transaction qualifiers and incomplete address masks prevent that claim. Earlier low-address matches at firmware Ethernet offsets 0x4288, 0x428c, 0x4308 and 0x430c are aliases, not four fully identified registers. This checkpoint does not promote those earlier candidates.

One conditional enable group constrains all fourteen captured address bits and targets 32 cells at candidate byte offset **0x1e04**, assuming CPU byte address >> 1. Its original register identity is unknown. All full-address predicates are available in `address-all-predicates.json`; next-data predicates for counter transitions are not register writes.

## Bus identities

Data balls, **unordered**: A5, A6, A7, A8, A9, B6, B8, B9, C1, D1, D2, D3, E1, E3, F1, F2. Their D0..D15 permutation remains unresolved.

Clock: H3 / `D0X0Y67.IOB[0]` -> BUFGMUX[15] I0 with S=0. The core path uses BUFGMUX[1]. Clock primitive gap endpoints remain in the flat HDL; the known fixed selections are structural path evidence, not a timing model.

Candidate controls: K1/K2 are the two active-low aperture selects; A11 is the output-enable candidate; J6 is a write-strobe candidate; G1 is an unresolved control/address-valid candidate. Select-to-0x60000000 versus 0x64000000 aperture assignment is unresolved. No nWAIT role is asserted.

Common tristate (1 means high impedance): `T = A11 | F | (K1 & K2)`, where F is `D0X17Y114.SLICE[1].AQ`, including its proven decoded replicas. All sixteen pads exhaustively match this function under the common-state relation. Thirty state aliases were established from identical canonical D/CE/SR/clock/initial settings; these are logical identities, not timing proof.

Address significance comes from configured increment/load functions. Slots 0..13 form the entire counter. An initial analysis mistakenly conditioned on the lowest carry-chain state and recovered only the upper thirteen bits. Excluding group state from external mode controls corrects that mistake; all fourteen bits are exhaustively replayed. Candidate CPU byte bits are slots + 1 for a 16-bit external bus. The physical ordering is proved within the decoded model; CPU scaling remains a correlation hypothesis because the current firmware-fit score uses aliased masks.

| Capture slot low to high | FPGA ball | Primary capture cell |
|---|---|---|
{pins}

Both aperture counters use the same lane order but have separate load/update conditions. Their nominal addresses are related only conditionally. `address-stage-projections.json` retains clock, enable, reset and sampled qualifier history for all 161 projections. These projections must not be treated as unconditional combinational equivalences or simultaneous equality of the two counters.

## Named register regions and candidate cones

The firmware/DICE region identities come from sealed phase 03. `register-bank-cones.json` indexes every compatible conditional group and offset; `conditional-register-groups.json` records masks, values, qualifier states and complete physical target lists. `conditional-cell-cones.jsonl` contains each target equation and its data/enable/reset cone. Candidate sets overlap heavily; **their sizes are search-space sizes, not recovered block sizes or coverage percentages**.

| Firmware region | Compatible predicate groups | Candidate physical cells | Unique full-address groups |
|---|---:|---:|---:|
{bank_table}

The listener region is 0x60000c00..0x60000c7f (four 0x20-byte banks); talker 0x60001200..0x6000127f. RTC/PTP RX/PTP TX begin at 0x60004000/4080/4100; SYS/MAC at 0x60004280/4300. Router/audio clock/InS/HPLL begin at 0x60005000/5100/5600/6000. These software labels alone do not identify implemented FPGA modules.

`fsmc-readback-cones.json` traces all sixteen physical data outputs through three FF boundaries, preserving intervening Boolean cells and opaque RAM/DSP/SRL sources. `decoder-qualifier-history.json` preserves five backward state levels from predicate qualifiers. `register-datapath-consumers.json` records first downstream FF data/enable/reset and typed BRAM address/data/write-enable consumers; it excludes global clock fanout. This supports physical tracing without inventing original hierarchy or signal names.

## Primitive behavior recovered

The new ILOGIC SDR input and OLOGIC SDR output/tristate models recover **108 I/O FFs**, preserving D, clock, CE, reset polarity, synchronous/asynchronous SR, INIT and SRVAL. Models apply only to the selected decoded non-DDR, non-latch, non-cascade configurations. Unclocked rank outputs use their decoded initial constants. DDR/serdes variants remain gaps. The pinned Combine ISE-hammer collector supplies the setting interpretation; AMD UG381 supplies the primitive architecture. No database bits were relabeled.

The flat output model has **{c['cone_equations']:,} equations**, {c['equation_ops']['ff']:,} FFs and **{c['equation_ops']['gap']:,} opaque endpoints**, down from 3,450 gap endpoints in phase 03. Boundary counts: {json.dumps(c['boundary_classes'],sort_keys=True)}.

The separate typed RAM model assembles **{len(ram)} logical storage groups**, backed by 164 physical 9-kbit halves, including companion halves needed for combined 18-kbit models. There are 95 originally referenced output-bearing halves; these denominators are not device utilization. It reconstructs decoded widths 1/2/4/9/18/36, data/parity addressing, mixed-width access, byte enables and READ_FIRST/WRITE_FIRST/NO_CHANGE for collision-free, one-port-at-a-time events. All captured RAM INIT contents are zero. Physical port identities and polarity are preserved in `bram-storage-models.json`.

**RAM behavior is an auxiliary typed storage model, not lowered into the flat Verilog.** Its 1,338 RAM gap outputs remain explicit there. Reset/output-register latency, EN_RSTRAM/RST_PRIORITY sequencing and cross-port collision timing are unresolved. DSP arithmetic, SRL and F7/F8 behavior, DDR/serdes and clock timing remain required for complete audio/network datapath simulation.

## Validation and reproducibility

- Raw versus simplified equation replay: **{a['compared_output_and_internal_values']:,} value comparisons**, **{a['compared_register_transition_inputs']:,} transition-input comparisons**, 64 deterministic abstract patterns; no skipped comparisons or encountered feedback failures.
- Counter arithmetic: {v['counter_increment_states']:,} increment states and {v['counter_load_vectors']:,} load vectors; all pass. All fourteen bits included in increment width.
- Shared data tristate: {v['tristate_truth_comparisons']} exhaustive comparisons; pass.
- RAM storage: 8,000 randomized mixed-width events against an independent bit-array reference plus three write-mode cases; pass within stated scope.
- Full partial-Verilog parse and hierarchy: Linux Yosys pass. No whole-design synthesis, formal equivalence, bus reachability or hardware validation is admitted.
- Scan limits are explicit in `address-predicate-limits.json`. Budget exclusions mean unprocessed, not absent logic. Periodic BDD reset avoids exhausting one cumulative node pool.

Input bitstream SHA-256: `945b2c3a0f74cd39825ec361da680c92303f20ac7f7a98756b7a829216ef9dbb`.
STM32 SHA-256: `b0979352e18a1093051fc6118a47694773cb9240e88087eca03aaa2ffe0f5e17`.
Project Combine: `01bdbb674f784740f977327b2edfe099ebf63ae0`; database SHA-256 `e44e5f9a7075854d653dc1bbb987ed9fe2a63098fcc5aee2a26521cf7f52ad10`. The seal rechecks vendor cleanliness and database identity. Parent phase 03 manifest, operator sources, official manual PDFs, exact run commands, logs and tool packages are hash-bound in the export.

## Exploratory transaction replay

This is a diagnostic experiment, **not an admitted bus protocol or register map**. It forces reset-release, supplies an assumed 8:1 core/bus event ratio, candidate strobes and all-ones external write data. Other pads and opaque primitives are zero; inactive clock domains retain INIT. Active enable counts do not identify written bit fields or prove hardware reachability. Results are preserved even if the assumed protocol fails to activate useful decoders.

| Select candidate | Address-valid candidate level | Candidate byte offset | Observed enabled candidate cells |
|---|---:|---|---:|
{tx}

## Remaining gaps and next decisive work

1. Derive the transaction-state machines and their actual reset/clock sequencing, prove the select-to-aperture assignments, and determine data-lane permutation. Current address masks and sampled history do not establish named-bank identity.
2. Resolve one firmware-supported write end to end through byte/halfword assembly and readback before propagating AVB/PTP/audio labels. Match both halves and actual field masks; a low-address match is insufficient.
3. Reconstruct the needed DDR/SRL/DSP variants, clock selectors and RAM reset/pipeline timing; then trace audio transport, RTC timestamp and AVB packet paths across those boundaries.
4. Retain the two unresolved HCLK set bits (main 8491 bit 513 and 8492 bit 512). This phase neither resolves nor assigns behavior to them.

No original HDL hierarchy, unique AVB/PTP/audio module identification, device interoperability or C++ readiness promotion is claimed.
'''
(B/'REPORT.md').write_text(text)
print('Report written',len(text),'characters')
