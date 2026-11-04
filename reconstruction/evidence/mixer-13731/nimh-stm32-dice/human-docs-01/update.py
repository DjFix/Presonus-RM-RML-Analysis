from pathlib import Path
import json,os,hashlib,re,datetime
from urllib.parse import unquote
R=Path.cwd().resolve();A=R/'reconstruction/artifacts';E=R/'reconstruction/evidence/mixer-13731/nimh-stm32-dice/human-docs-01';E.mkdir(parents=True,exist_ok=True)
modified=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def link(label,target,parent):
 target=Path(target);assert target.exists(),target
 url=os.path.relpath(target,parent)
 return f'[{label}](<{url}>)' if ' ' in url else f'[{label}]({url})'
def save(p,text):
 p=Path(p)
 if p.exists():
  old=E/'before'/p.relative_to(R);old.parent.mkdir(parents=True,exist_ok=True)
  assert not old.exists(),old
  old.write_bytes(p.read_bytes())
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text);modified.append(p)
master=A/'mixer-13731/nimh-stm32-dice/README.md'
registry=R/'reconstruction/shared/extraction/embedded-mcu-01'
manual=R/'doc/DICE_III_User_Guide/TCD30xx - Firmware Development.pdf'
components={}
for manifest in sorted(A.glob('*/*/manifest.json')):
 d=manifest.parent;fw=d.parent.name;component=d.name;m=json.loads(manifest.read_text());files=m.get('binaries',m.get('files',[]))
 # These are the component manifests created by this task's extraction trial.
 if not files or 'container_release' not in m:continue
 components.setdefault(component,[]).append(d)
 ref=lambda label,p:link(label,p,d)
 text=f'# {component} — {fw}\n\nHuman entry point for architecture, findings and remaining work. '
 text+='The directory names the containing host release; it does not establish the embedded firmware version.\n\n'
 if component=='nimh-stm32-dice' and fw=='mixer-13731':
  text+='''## Architecture

The NIMH AVB card contains an STM32F103ZET6 Cortex-M3 and a Spartan-6 FPGA.
Together they implement the logical DICE control/peripheral role. This is a functional
architecture description, not a claim of identical internals to an integrated DICE chip.
The STM32 image has an eCos runtime, TCAT SDK layers and application command handlers.

```mermaid
flowchart LR
    H[Linux host application] --> S[STM32 SPI1 and DMA1 channel 2]
    S --> B[1024-byte circular RX buffer]
    B --> P[SysEx framing and packet queues]
    P --> C[Command dispatcher]
    C --> W[Deferred rate/link worker]
    C --> D[TCAT SDK boundaries]
    W --> D
    D -. partially traced .-> F[FPGA-backed peripherals]
```

## Architectural patterns

- Follow application → SDK/DAL → HAL/peripheral boundaries from the local TCAT documentation.
- Separate immediate command acceptance from deferred completion. An ACK does not prove clock lock.
- Treat DMA production, framing, queue publication, dequeue and release as distinct stages.
- Match RTOS/library source before manually reconstructing equivalent runtime code.
- Use architecture patterns from documentation; no direct CS18/RM DICE binary mapping is used here.

## Established findings

| Area | Finding | Scope |
|---|---|---|
| Startup | Flash base `0x08000000`; initial SP `0x20010000`; VTOR moved to SRAM `0x20000000` | Bounded native reset replay; no complete boot |
| Runtime | eCos/TCAT family, 124 CLI records, 24 SDK source-path strings | Exact vendor revision unresolved |
| Versions | Application banner `1.5.5.0`; SDK banner `1.0.0.0 local beta` | Neither is an eCos release identifier |
| Host commands | Rate/link `0x11`, clock source `0x28`, routing `0x16` | 27 host packet-construction cases; modeled transport boundaries |
| Dispatcher | Command decoding, ACKs and selected SDK calls | 222 dispatcher and 12 deferred-consumer cases |
| Receive path | SPI1 → DMA1 channel 2 → buffer at `0x2000cd14` → parser → queue | 20 framing/queue, 3 alternate-queue and 4 receive-to-dispatch cases |
| FPGA-facing access | Mixer callback writes `0x60005204` | 216 native replay cases against RAM-backed register page |

## Open questions

- Exact eCos/TCAT source revision and original embedded declarations/function boundaries.
- Deferred clock/rate transition completion, error propagation and lock confirmation.
- Physical DMA/interrupt behavior, scheduler concurrency and overrun timing.
- Full SDK-to-FPGA interface ownership, register semantics and board signal assignments.
- Hardware interoperability and audio behavior; no hardware validation has been performed.

## Reports and evidence

'''
  for label,p in [('Architecture, runtime and command-path report',d/'analysis/command-paths.md'),('SPI/DMA receive report',d/'analysis/receive-path.md'),('Memory layout',d/'memory-layout/README.md'),('Runtime identification',d/'runtime-identification/README.md'),('Command-map proof',R/'reconstruction/evidence/mixer-13731/nimh-stm32-dice/jobs/command-map-01/validation.json'),('Receive replay and explicit boundary models',R/'reconstruction/evidence/mixer-13731/nimh-stm32-dice/jobs/spi-rx-02/replay.json'),('Receive validation proof',R/'reconstruction/evidence/mixer-13731/nimh-stm32-dice/jobs/spi-rx-02/validation.json'),('Local TCAT architecture guide',manual),('Paired FPGA component',A/'mixer-13731/nimh-fpga-dice/README.md')]:text+='- '+ref(label,p)+'\n'
 else:
  text+='## Architecture and patterns\n\n'
  if component.endswith('stm32-dice'):
   text+='This is a separate raw STM32 firmware family embedded in the Linux mixer application. Startup/header inspection supports STM32 flash/RAM and Thumb code; exact board/part assignment for NOAA and ESA remains unresolved in this work.\n\n'
   if component=='nimh-stm32-dice':text+='The NIMH card combines MCU control with FPGA-backed peripherals. '
   text+='Use '+ref('the NIMH architecture study',master)+' as a documented analysis pattern. Its tested behavior and runtime version do not automatically apply to this release or image family.\n\n'
   findings='Original bytes, ELF symbol identity, offsets and hashes are recorded. No command-path or complete boot replay for this particular version is claimed here.'
   questions='Confirm board identity and embedded version; map startup and runtime dependencies; trace host commands and device boundaries; validate behavior for this exact image.'
  elif component.endswith('fpga-dice'):
   text+='This is an FPGA programming payload extracted from a host ELF, separate from executable MCU firmware. Preserve container/compression identity separately from the decoded bitstream and any derived netlist.\n\n'
   if component=='nimh-fpga-dice':text+='For NIMH, board/format evidence identifies a Spartan-6 XC6SLX45; STM32 and FPGA share the logical DICE role. Hardware partitioning and board signal names need independent evidence.\n\n'
   findings='The extraction preserves original payload bytes and source identity. Extraction alone does not recover HDL, establish primitive behavior or prove hardware equivalence.'
   questions='Bind compressed payload to decoded-image hashes; identify device/format per variant; recover functional modules and physical interfaces; verify sequential behavior and hardware timing.'
  elif component=='panel':
   text+='Panel-controller firmware is separate from the AVB STM32 images. Initial SP `0x10002000` and reset pointers near zero are useful architecture clues. The user identifies the panel MCU as LPC1317F; byte/header evidence alone does not independently establish that exact part.\n\n'
   findings='Separate panel image objects and original hashes are retained. Their names do not establish board wiring, protocol semantics or interchangeability.'
   questions='Corroborate exact MCU/board identity, vector and memory layout, GPIO mapping, host transport and panel-control behavior.'
  elif component=='dice3':
   text+='The surface contains integrated DICE III firmware with an ARM926/ARM9EJ-S core, not Cortex-M. Its boot format and peripheral architecture must be treated separately from the NIMH STM32. Use the local TCAT manuals for architecture patterns.\n\n'
   findings='The exact `_ZL18dice3_surface_code` export is 230,512 bytes. It has a TCAT boot header and ARM entry at offset `0x200`; preserve the exact symbol range rather than a padded derivative.'
   questions='Map integrated-processor startup and runtime, application interfaces and command completion. Shared architectural roles do not establish binary compatibility with NIMH.'
  else:
   text+='The Linux application is the container and host-side control endpoint for embedded programming payloads. Original ELF symbols identify host functions and data; they do not name functions inside raw embedded images.\n\n'
   findings='This task retains extracted update-script data and shared input/provenance. It has not migrated or consolidated the broader application reconstruction owned by other tasks.'
   questions='Connect exact host symbols to packet construction and transport; distinguish upload/erase paths from runtime commands; link the separately maintained application reconstruction when available.'
  text+='## Established findings\n\n'+findings+'\n\nStatus: `'+m.get('status','extracted-bytes-verified')+'`. No new behavior, ABI or hardware validation is implied by this README.\n\n## Open questions\n\n'+questions+'\n\n## Reports and evidence\n\n'
  for label,p in [('Cross-version extraction report',registry/'REPORT.md'),('Original symbols, ranges and source hashes',registry/'manifest.json'),('Extraction byte verification',registry/'linux-verification.json'),('Local TCAT architecture guide',manual)]:text+='- '+ref(label,p)+'\n'
  if component=='nimh-fpga-dice':
   external=R/'evidence/recovery/2026-10-27/nimh-fpga-connectivity-02/REPORT.md'
   if external.exists():text+='- '+ref('Related FPGA connectivity report (separate task; check its input hashes before reuse)',external)+'\n'
 text+='\n## Firmware and identity\n\n'+ref('Component manifest',manifest)+' records identities and validation limits.\n\n'
 for f in files:
  p=d/f['path'];text+='- '+ref(str(Path(f['path']).parent.name)+' / '+Path(f['path']).name,p)+'\n'
 text+='\n'+ref('All components and releases',R/'reconstruction/README.md')+'\n' if (R/'reconstruction/README.md').exists() else '\n[All components and releases](../../../README.md)\n'
 save(d/'README.md',text)
# Root entry point: primary component knowledge, then release-specific manifests.
root=R/'reconstruction/README.md'
text='''# Reconstruction: architecture and findings

Start with a component README. It summarizes architecture, useful patterns, established
findings and open questions, then links to reports, exact binaries and validation evidence.
Container releases and embedded firmware versions are tracked separately.

## Components

| Component | Start here | Current scope in this task |
|---|---|---|
'''
labels={'nimh-stm32-dice':'NIMH MCU: architecture, runtime and command paths','nimh-fpga-dice':'NIMH FPGA: payload and related connectivity work','noaa-stm32-dice':'NOAA MCU','noaa-fpga-dice':'NOAA FPGA','esa-stm32-dice':'ESA MCU','esa-fpga-dice':'ESA FPGA','panel':'Panel controller','dice3':'Surface integrated DICE III','app':'Linux host application inputs'}
for c,dirs in components.items():
 d=next((p for p in dirs if p.parent.name=='mixer-13731'),dirs[0]);scope='Bounded offline native replay' if c=='nimh-stm32-dice' else 'Extraction and linked evidence; broader work remains separate'
 text+=f'| `{c}` | '+link(labels.get(c,c),d/'README.md',root.parent)+f' | {scope} |\n'
text+='''
Marvell switch configuration, OMAP DSP, faderboard firmware and its bootloader have
no deliverables from this task in this tree yet. Their absence is not a claim that no
other task has studied them.

## Release-specific entry points

'''
for fw in sorted({p.parent.name for ds in components.values() for p in ds}):
 text+='- **'+fw+'**: '+', '.join(link(c,d/'README.md',root.parent) for c,ds in sorted(components.items()) for d in ds if d.parent.name==fw)+'\n'
text+='\n## Reading the evidence\n\n'+link('Shared inputs, upstream sources and extraction provenance',R/'reconstruction/shared/README.md',root.parent)+' support the component findings. `artifacts/` contains useful results; `evidence/` retains operational jobs, frozen proofs and logs. Earlier proof hashes describe their recorded snapshots; documentation edits are recorded separately and do not add behavioral validation.\n'
save(root,text)
shared=R/'reconstruction/shared/README.md';save(shared,'# Shared reconstruction inputs and references\n\n'+link('Start with component architecture and findings',root,shared.parent)+'. Shared data below supports those human-facing summaries.\n\n'+shared.read_text().split('\n',1)[1])
# Validate local links in every edited README, including encoded source PDF paths.
checked=0
for p in modified:
 for url in re.findall(r'\]\(([^\n]*?)\)',p.read_text()):
  url=url.strip('<>')
  if '://' in url or url.startswith('#'):continue
  assert (p.parent/unquote(url.split('#')[0])).exists(),(p,url)
  checked+=1
proof={'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'documentation-links-verified','component_readmes':sum(len(ds) for ds in components.values()),'local_links_checked':checked,'files':{str(p.relative_to(R)):sha(p) for p in modified},'behavioral_replay':False,'prior_layout_proof_preserved':True,'originals_deleted':0}
(E/'validation.json').write_text(json.dumps(proof,indent=2)+'\n')
(E/'update.py').write_bytes(Path(__file__).read_bytes())
print('PASS:',proof['component_readmes'],'component READMEs;',checked,'local links;',len(modified),'updated files')
