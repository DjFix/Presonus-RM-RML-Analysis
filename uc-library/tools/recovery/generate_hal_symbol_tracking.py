"""Evidence-separated HAL priority index; never changes readiness ledgers."""
from pathlib import Path
import hashlib,json,re
r=Path.cwd();lib=r/'uc-library';out=r/'evidence/recovery/2026-10-29/surface-hal-priority';out.mkdir(parents=True,exist_ok=True);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();coverage=json.loads((lib/'tracking/coverage.json').read_text());ready=json.loads((lib/'validation/ready-functions.json').read_text())['functions'];pending=json.loads((lib/'validation/compiled-functions.json').read_text())['functions'];R={(x['original_elf_sha256'],x['mangled']):x for x in ready};P={(x['original_elf_sha256'],x['mangled']):x for x in pending};assert R.keys().isdisjoint(P);cache={}
def current(row):
 for n,h in row.get('sources',{}).items():
  p=lib/n
  if p not in cache:cache[p]=sha(p) if p.is_file() else None
  if cache[p]!=h:return False
 for n,h in row.get('repository_sources',{}).items():
  p=r/n
  if p not in cache:cache[p]=sha(p) if p.is_file() else None
  if cache[p]!=h:return False
 return True

def category(name):
 if re.search(r'Presonus::ScribbleStripMgr',name):return 'display-draw'
 if re.search(r'Presonus::Surface::(?:SLMixerHandler|MixerAssignmentHandler|AssignmentHandler)',name):return 'panel-control-handlers'
 if re.search(r'Firmware|Updater|UpdateComponent|UpdateManager|BootLoader|Programmer|Flash',name):return 'update-offline'
 if re.search(r'Presonus::Panel::|Presonus::Surface::(?:Panel|LCD|Display)|Presonus::(?:MainLCDComponent|DisplayManager|UARTMessage|FPGA|GPIO|I2C|SPI)',name):
  if re.search(r'LCD|Display|Bitmap|Font|Draw|TextEntry',name):return 'display-draw'
  if re.search(r'Fader|Switch|Button|LED|Encoder|PotControl|DigitalPot|OutputPin|InputGPIO',name):return 'controls-io'
  return 'panel-transport-operations'
 if re.search(r'Presonus::Dsp::Fader(?:Curve)?Interpolator',name):return 'controls-io'
 return None
rows=[];inputs={}
for role,data in coverage['roles'].items():
 manifest=lib/f'recovered-all/{role}/manifest.json';m=json.loads(manifest.read_text());inputs[str(manifest.relative_to(r))]=sha(manifest)
 for x in data['symbols']:
  kind=category(x.get('demangled',''))
  if not kind or not x['defined'] or not x['size']:continue
  owner=re.search(r'N[KVR]*([0-9]+)([A-Za-z_][A-Za-z_0-9]*)',x['mangled']);core_owned=bool(owner and owner.group(1)=='4' and owner.group(2).startswith('Core'))
  if core_owned:kind='upstream-source-dependency'
  key=(m['sha256'],x['mangled']);entry=R.get(key) or P.get(key);status='ready-ledger' if key in R else 'declaration-pending' if key in P else 'not-admitted'
  if core_owned and entry is None:status='CCL source available; binding pending' if x.get('upstream_body_available') else 'CCL source adaptation pending; no binary reconstruction'
  fresh=current(entry) if entry else None
  if entry and not fresh:status+='; active-refresh-pending'
  rows.append(dict(role=role,priority=kind,upstream_body_available=x.get('upstream_body_available',False),upstream_api_match=x.get('upstream_api_match',False),mangled=x['mangled'],demangled=x['demangled'],address=x['address'],size=x['size'],section=x['section'],kind=x['kind'],firmware_version='CS18AI13840' if role=='client' else 'RM13731',elf_sha256=m['sha256'],elf_path=m['path'],status=status,source_bindings_current=fresh,bytes_extracted=x.get('bytes_extracted',False),bytes_verified=x.get('bytes_verified',False),pseudocode_exported=x.get('pseudocode_exported',False),cpp_compiled=bool(entry and entry.get('cpp_compiled')),mangling_checked=bool(entry and entry.get('mangling_namespace_checked')),behavior_domain=entry.get('domain','') if entry else '',hardware_verified=bool(entry and entry.get('hardware_verified')),evidence=entry.get('validation') if entry else (x.get('pseudocode') or x.get('machine_code') or '').removeprefix('../')))
summary={role:{'function_records':sum(x['role']==role and x['kind']=='STT_FUNC' for x in rows),'data_records':sum(x['role']==role and x['kind']!='STT_FUNC' for x in rows)} for role in coverage['roles']};report=dict(scope='Priority candidate selection by explicit class/name rules; agent inventories must refine drawing/driver/OSS ownership. Entire-project SYMBOLS.md remains authoritative. No ready status added or hardware claim.',selection_function=Path(__file__).read_text().split('def category(name):')[1].split('rows=[]')[0],inputs=inputs,ledger_sha256={n:sha(lib/'validation'/n) for n in ['ready-functions.json','compiled-functions.json']},summary=summary,symbols=rows)
(out/'hal-priority-symbols.json').write_text(json.dumps(report,indent=2)+'\n')
text='# HAL priority symbol index\n\nPrioritize CS18AI surface system update (offline), panel operations, fader control/readout, scribble-strip drawing, buttons, LEDs, encoders and pots. Use available OSS source first: verify exact identity/API, pin source and licenses, then recover application-specific gaps. Core stays pinned CCL source; never binary-reconstruct it.\n\nThis focused index does not replace [the complete tracker](SYMBOLS.md). Selection is explicit and provisional; reviewers must add missed HAL ownership and exclude unrelated matches. `active-refresh-pending` means current batch changes invalidated an old source binding; it is not fresh validation. Embedded MCU/FPGA artifacts remain separate architecture/data workloads. Hardware testing and any flash/erase execution are excluded.\n\n'
for role in ['client','server']:
 if role not in summary:continue
 m=json.loads((lib/f'recovered-all/{role}/manifest.json').read_text());text+=f"## {role}: {m['path']}\n\nELF SHA-256 `{m['sha256']}`.\n\n"
 for label,isfunc in [('Functions',True),('Data and ABI metadata',False)]:
  text+='### '+label+'\n\n|Category|Original mangled name / demangled name|Address / size / section|Bytes extracted / verified|Pseudocode|C++ / mangling|Status|Behavior domain / HW verified|Evidence|\n|---|---|---|---|---|---|---|---|---|\n'
  for x in sorted((x for x in rows if x['role']==role and (x['kind']=='STT_FUNC')==isfunc),key=lambda x:(x['priority'],x['address'],x['mangled'])):
   evidence=x['evidence'];link=f'[{"proof" if x["cpp_compiled"] else "analysis"}]({evidence})' if evidence else 'none';name=x['demangled'].replace('|','\\|');text+=f"|{x['priority']}|`{x['mangled']}`<br>{name}|`0x{x['address']:x}` / {x['size']} / {x['section']}|{int(x['bytes_extracted'])} / {int(x['bytes_verified'])}|{int(x['pseudocode_exported'])}|{int(x['cpp_compiled'])} / {int(x['mangling_checked'])}|{x['status']}|{x['behavior_domain'].replace(chr(124),chr(47)) or 'not validated'} / {int(x['hardware_verified'])}|{link}|\n"
  text+='\n'

text+='## Validated candidates awaiting canonical admission\n\nThe tables above reflect canonical ledger status; candidate checks do not promote records.\n\n'
for candidate in ['cs18-motorized-fader','cs18-encoder-control','cs18-blink-led','cs18-input-gpio','surface-fader-commands']:
 own=lib/'candidates'/candidate
 control=own/'CONTROLLED-APPLY.json';proof=own/'NATIVE-VALIDATION.json'
 if not control.exists() or not proof.exists():continue
 c=json.loads(control.read_text());v=json.loads(proof.read_text())
 if not v.get('passed'):continue
 for item in c.get('products',[]):
  q=lib/item['source'];assert sha(q)==item['sha256'],str(q)
 text+=f'- [{candidate}](candidates/{candidate}/SYMBOLS.md): candidate-only source/native validation; [proof](candidates/{candidate}/NATIVE-VALIDATION.json), SHA-256 `{sha(proof)}`. Original declarations, source/role admission and hardware status retain their explicit separate limits.\n'
(lib/'HAL_SYMBOLS.md').write_text(text);print(json.dumps(summary))
