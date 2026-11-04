from pathlib import Path
import json,os,re,hashlib,datetime
from urllib.parse import unquote
R=Path.cwd().resolve();H=R/'reconstruction/hw';E=R/'reconstruction/evidence/mixer-13731/nimh-stm32-dice/hardware-docs-01';E.mkdir(parents=True,exist_ok=True)
changed=[]
def link(label,p,parent):
 p=Path(p);assert p.exists(),p
 return '['+label+'](<'+os.path.relpath(p,parent)+'>)'
def save(p,text):
 p=Path(p)
 if p.exists():
  b=E/'before'/p.relative_to(R);b.parent.mkdir(parents=True,exist_ok=True);assert not b.exists();b.write_bytes(p.read_bytes())
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text);changed.append(p)
records={}
for p in sorted((R/'reconstruction/artifacts').glob('*/*/README.md')):
 if (p.parent/'manifest.json').exists():records.setdefault(p.parent.name,[]).append(p)
maphw={k:k for k in records if k!='app'};maphw['app']='host'
for sw,paths in records.items():
 hw=maphw[sw];d=H/hw;d.mkdir(parents=True,exist_ok=True)
 primary=next((p for p in paths if p.parent.parent.name=='mixer-13731'),paths[0]);s=primary.read_text()
 pattern=r'## Architecture(?: and patterns)?\n(.*?)(?=\n## Established findings)'
 match=re.search(pattern,s,re.S);architecture=match.group(1).strip() if match else 'Physical interfaces and board identity remain to be established.'
 if hw=='host':architecture='The host is the physical Linux application processor and its board interfaces. Application ELF versions are software extraction points, not hardware identities. Mixer processor details and board revisions need source-backed identification; no surface/mixer processor equivalence is assumed.'
 if hw=='nimh-stm32-dice':architecture+='\n\nThe command and receive paths below describe observations from one software image; they constrain the hardware model without establishing all board behavior.'
 text=f'# {hw}: hardware knowledge\n\nCanonical component description, independent of the release used to extract software. Physical board revisions remain separate identities when evidence shows a difference.\n\n## Architecture and patterns\n\n'+architecture+'\n\n## Findings and their scope\n\n'
 if hw=='nimh-stm32-dice':
  text+='''- Board/photo evidence identifies STM32F103ZET6 and board marking `400-XMEN-NIMH-C`.
- Software observation: mixer-13731 NIMH code programs SPI1 data register `0x4001300c`, DMA1 channel 2 and a 1,024-byte receive buffer at `0x2000cd14`. Native setup and parsing were replayed with RAM-backed registers and modeled scheduling.
- Software observation: a native mixer-control callback writes external address `0x60005204`. The complete bus/register implementation and physical wiring remain unresolved.
- eCos, TCAT SDK banners, queue layout and command opcodes are software properties. They are evidence about interfaces, not permanent attributes of the MCU silicon.

'''
 else:
  findings=re.search(r'## Established findings\n(.*?)(?=\n## Open questions)',s,re.S)
  text+=(findings.group(1).strip() if findings else 'No additional hardware behavior validated in this task.')+'\n\n'
 text+='A firmware release does not define a new hardware component. Software-derived observations retain their image identity and tested domain; they are not silently generalized across versions or physical board revisions.\n\n## Open questions\n\n'
 questions=re.search(r'## Open questions\n(.*?)(?=\n## Reports and evidence)',s,re.S)
 text+=(questions.group(1).strip() if questions else 'Identify physical board revisions, pins, peripheral ownership and runtime behavior.')+'\n\n## Reports and evidence\n\n'
 text+='- '+link('Architecture and extraction report',R/'reconstruction/shared/extraction/embedded-mcu-01/REPORT.md',d)+'\n'
 if hw=='nimh-stm32-dice':
  for label,t in [('Command and SDK architecture',primary.parent/'analysis/command-paths.md'),('SPI/DMA receive findings',primary.parent/'analysis/receive-path.md'),('Command-map validation',R/'reconstruction/evidence/mixer-13731/nimh-stm32-dice/jobs/command-map-01/validation.json'),('Receive-path evidence',R/'reconstruction/evidence/mixer-13731/nimh-stm32-dice/jobs/spi-rx-02/replay.json')]:text+='- '+link(label,t,d)+'\n'
 if hw=='nimh-fpga-dice':
  t=R/'evidence/recovery/2026-10-27/nimh-fpga-connectivity-02/REPORT.md'
  if t.exists():text+='- '+link('Related FPGA task report; bind its input hashes before reuse',t,d)+'\n'
 text+='- '+link('TCAT architecture documentation',R/'doc/DICE_III_User_Guide/TCD30xx - Firmware Development.pdf',d)+'\n\n## Software extraction points\n\n'
 for p in paths:text+='- '+link(p.parent.parent.name,p,d)+'\n'
 text+='\n[How discoveries update hardware knowledge](../README.md#updating-the-hardware-model)\n'
 save(d/'README.md',text)
# Unstudied physical components: no fabricated findings or fake artifact directories.
for hw,description in [('nimh-marvell','The AVB-card switch is a separate physical component. Its model, port wiring, reset/clock interfaces and configuration path are not established by this task.'),('dsp','The user identifies internal mixer DSP code on OMAP. Processor identity, DSP memory map and host/DSP interfaces remain to be corroborated here.'),('faderboard','The user identifies EFM32 firmware and bootloader for the faderboard. Both software payloads belong to this physical component; exact MCU and board revision, boot layout and transport remain unverified here.')]:
 save(H/hw/'README.md',f'# {hw}: hardware knowledge\n\n## Architecture and patterns\n\n{description}\n\n## Findings\n\nTracking entry only. No hardware analysis or validated extraction for this component was added by this task.\n\n## Open questions\n\nIdentify source-backed part/board identity, interfaces, memory/boot layout and revision differences. Record new software observations with image hashes and validation scope.\n\n## Reports and evidence\n\nNo component-specific evidence admitted here yet. [Discovery workflow](../README.md#updating-the-hardware-model).\n')
index='''# Hardware architecture and discovery

Start here for the physical system. Components are independent of the software release
that exposed them. Keep distinct board revisions where evidence establishes differences.
The MCU and FPGA records describe parts of an AVB card; shared DICE functionality is
an architectural relationship, not binary or hardware equivalence.

## Components

'''
for p in sorted(H.glob('*/README.md')):index+='- '+link(p.parent.name,p,H)+'\n'
index+='''
## Updating the hardware model

1. Before extraction or reconstruction, read the component README and its open questions.
   Use its known processor, memory, boot and interface constraints to guide analysis.
2. Record each new observation in evidence: source ELF/blob SHA-256, container release,
   original symbol/range or embedded address, method, outcome and bounded validation domain.
3. Reconcile the observation with this hardware description. Mark it as board/document
   evidence, software-observed behavior, inference, user-reported information or unresolved.
   Software programming a register proves the observed code path; it alone does not prove
   wiring, physical timing or implementation of the peripheral.
4. Correct the canonical component README and open questions when warranted, citing the
   new evidence. Preserve the previous statement and reason in the discovery journal.
   Conflicting observations remain visible until resolved; do not overwrite uncertainty.
5. Keep runtime versions, SDK identity and version-specific behavior in software artifacts.
   Link those extraction points back to the hardware model. A version change alone does
   not create another hardware component; a proven physical revision can.

## Discovery journal

- 2026-10-28: separated physical component knowledge from software extraction points.
  Existing software observations are retained with their original validation limits.
  Faderboard application and bootloader map to the same physical board. `app` maps to
  the host processor rather than a fictional hardware component named app.

[Software results by release](../README.md#software-extraction-points) · [Shared provenance](../shared/README.md)
'''
save(H/'README.md',index)
# Replace duplicated architecture in software entry points with canonical link.
for sw,paths in records.items():
 for p in paths:
  s=p.read_text();hw=H/maphw[sw]/'README.md'
  section='## Hardware model\n\n'+link('Canonical '+maphw[sw]+' architecture, patterns, findings and open questions',hw,p.parent)+'. Read this before analyzing the image. New software observations must be reconciled with that model and cited with their source identity and validation scope.\n'
  s=re.sub(r'## Architecture(?: and patterns)?\n.*?(?=\n## Established findings)',section,s,flags=re.S)
  s=s.replace('Human entry point for architecture, findings and remaining work.','Software extraction and validation record. Hardware architecture is maintained separately.')
  s=s.replace('## Open questions','## Software reconstruction questions')
  save(p,s)
root=R/'reconstruction/README.md';s=root.read_text();start=s.index('## Components');end=s.index('## Release-specific entry points')
s=s[:start]+'## Hardware components\n\n'+link('Start with the version-independent hardware model',H/'README.md',root.parent)+'. Each physical component README consolidates architecture, patterns, findings, evidence and open questions.\n\n## Software extraction points\n\nThe entries below identify software containers, not hardware variants. Read the linked hardware description first; use new software evidence to correct or refine it.\n\n'+s[end:]
s=s.replace('Start with a component README. It summarizes architecture, useful patterns, established\nfindings and open questions, then links to reports, exact binaries and validation evidence.','Start with `hw/` for hardware architecture and open questions. Then follow a software\nextraction point for exact binaries, version-specific reports and validation evidence.')
save(root,s)
shared=R/'reconstruction/shared/README.md';save(shared,shared.read_text()+'\n'+link('Canonical hardware knowledge',H/'README.md',shared.parent)+' guides extraction and receives evidence-backed corrections from software analysis.\n')
count=0
for p in changed:
 for url in re.findall(r'\]\(([^\n]*?)\)',p.read_text()):
  url=url.strip('<>')
  if '://' in url or url.startswith('#'):continue
  assert (p.parent/unquote(url.split('#')[0])).exists(),(p,url)
  count+=1
(E/'update.py').write_bytes(Path(__file__).read_bytes())
(E/'validation.json').write_text(json.dumps({'status':'documentation-links-verified','created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in changed},'hardware_components':len(list(H.glob('*/README.md'))),'local_links_checked':count,'behavioral_replay':False,'original_data_deleted':0},indent=2)+'\n')
print('PASS:',len(list(H.glob('*/README.md'))),'hardware component descriptions;',count,'local links;',len(changed),'updated documents')
