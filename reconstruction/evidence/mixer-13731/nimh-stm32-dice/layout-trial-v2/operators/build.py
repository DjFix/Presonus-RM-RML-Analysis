from pathlib import Path
import hashlib,json,shutil,os,re,datetime,urllib.parse
R=Path.cwd().resolve();W=R/'temp/recovery-work/layout-trial-v2';S=W/'stage';S.mkdir(exist_ok=True)
V1=R/'reconstruction/artifacts/mixer-13731/nimh-stm32-dice/migration/manifest.json';old=json.loads(V1.read_text());rows=old['files'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert len(rows)==2990
owned={x['destination']:x['destination_sha256'] for x in rows}
for folder in ['reconstruction/artifacts/mixer-13731/nimh-stm32-dice/migration','reconstruction/evidence/mixer-13731/nimh-stm32-dice/migration']:
 for p in (R/folder).rglob('*'):
  if p.is_file():owned.setdefault(str(p.relative_to(R)),sha(p))
for p,h in owned.items():assert sha(R/p)==h,('v1 changed',p)
for x in rows:assert sha(R/x['source'])==x['source_sha256'],('original changed',x['source'])
P='reconstruction/artifacts/mixer-13731/nimh-stm32-dice';E='reconstruction/evidence/mixer-13731/nimh-stm32-dice';C='reconstruction/shared/extraction/embedded-mcu-01';U='reconstruction/shared/upstream/ecos/2580ee933ff5bed1f39c18c882f2e1593d980ef6'
MAP={};generated={};copied={}
def write(p,text):
 p=Path(p);q=S/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(text);generated[str(p)]=True

def copy(src,dst):
 src=Path(src);dst=str(dst);q=S/dst;q.parent.mkdir(parents=True,exist_ok=True)
 if q.exists():assert sha(q)==sha(R/src),('collision',src,dst)
 else:shutil.copy2(R/src,q)
 MAP[str(src)]=dst;copied[dst]=str(src)

for row in rows:
 src=row['source'];d=row['destination'];p=Path(src);name=p.name
 if '/xmen-stm32/images/' in src:
  bits=Path(d).parts;fw,comp=bits[2],bits[3]
  dst=f'reconstruction/artifacts/{fw}/{comp}/firmware/{p.parent.name}/{name}'
 elif '/xmen-stm32/inputs/' in src:
  dst=f'reconstruction/shared/inputs/{row["source_sha256"]}/{name}'
 elif src.startswith('evidence/recovery/2026-10-27/xmen-stm32/'):
  rel=src.split('/xmen-stm32/',1)[1]
  dst=f'{C}/{rel}' if name in ('manifest.json','linux-verification.json','REPORT.md','tracker-fragment.md') else f'reconstruction/evidence/mixer-13731/app/extraction-01/{rel}'
 elif src.startswith('evidence/recovery/2026-10-27/nimh-command-map/'):
  rel=src.split('/nimh-command-map/',1)[1]
  if name=='REPORT.md':dst=f'{P}/analysis/command-paths.md'
  elif name=='dispatch-table.json':dst=f'{P}/command-paths/{name}'
  elif name in ('cli-registrations.json','sdk-source-paths.json','version-banner.json'):dst=f'{P}/runtime-identification/{name}'
  elif name in ('ecos-source.json','ecos-reference-2580ee933ff5.tar.gz','ecos-reference-hal_misc.c','ecos-3.0-branchpoint-hal_misc.c'):dst=f'{U}/{name}'
  else:dst=f'{E}/jobs/command-map-01/{rel}'
 elif src.startswith('evidence/recovery/2026-10-28/nimh-spi-rx/'):
  rel=src.split('/nimh-spi-rx/',1)[1]
  dst=f'{P}/analysis/receive-path.md' if name=='REPORT.md' else f'{P}/receive-path/disassembly.thumb.txt' if name=='receive-path.thumb.txt' else f'{E}/jobs/spi-rx-02/{rel}'
 elif src.startswith('uc-library/tools/recovery/nimh-command-map/'):
  dst=f'{E}/jobs/command-map-01/operators-maintained-snapshot/{name}'
 elif src.startswith('uc-library/validation/nimh-command-map/'):
  rel=src.split('uc-library/validation/nimh-command-map/',1)[1];dst=f'{E}/history/legacy-validation-index/{rel}'
 elif src.startswith('temp/recovery-work/nimh-spi-rx/'):
  dst=f'{E}/jobs/spi-rx-02/working/{name}'
 elif src.startswith('temp/embedded-mcu/'):
  dst='reconstruction/evidence/mixer-13731/app/extraction-01/working/'+src.split('temp/embedded-mcu/',1)[1]
 else:
  assert src.startswith('evidence/recovery/2026-10-28/vm-migration/legacy-uc-recovery/nimh-command-map/')
  dst=f'{E}/history/legacy-command-map/'+src.split('/legacy-uc-recovery/nimh-command-map/',1)[1]
 copy(src,dst)
# Preserve the complete prior layout records as historical evidence, not current deliverables.
for src in owned:
 if '/migration/' in src:
  rel=src.split('/migration/',1)[1]
  prefix='artifacts' if '/artifacts/' in src else 'evidence'
  copy(src,f'{E}/layout-trial-v2/prior-layout/{prefix}/{rel}')
# Only final Markdown navigation is transformed. Historical proofs, snapshots and sources stay exact.
link_audit=[]
for src,dst in list(MAP.items()):
 p=S/dst
 if p.suffix!='.md' or '/history/' in dst or '/prior-layout/' in dst or p.name.startswith('SYMBOLS-before'):continue
 def fix(match):
  url=match.group(1).strip('<>');path,sep,fragment=url.partition('#');path=urllib.parse.unquote(path)
  if '://' in path or not path:return match.group(0)
  target=None
  for c in [(R/src).parent/path,R/'uc-library'/path,R/path]:
   try:key=str(c.resolve().relative_to(R))
   except ValueError:continue
   if key in MAP:target=MAP[key];break
   if c.exists():target=key;break
  if target is None:
   # Prior tracker fragments are location-dependent historical material.
   link_audit.append(dict(file=dst,target=url));return match.group(0)
  rel=os.path.relpath(R/target,(R/dst).parent)+(sep+fragment if sep else '')
  return '](<'+rel+'>)' if ' ' in rel else ']('+rel+')'
 p.write_text(re.sub(r'\]\(([^\n]*?)\)',fix,p.read_text()))
# Public useful results: source identity and bounded domains are never inferred from storage names.
firmware={}
for src,dst in MAP.items():
 if '/firmware/' in dst:
  key='/'.join(Path(dst).parts[:4]);firmware.setdefault(key,[]).append(dict(path=os.path.relpath(dst,key),sha256=sha(S/dst),bytes=(S/dst).stat().st_size,original_path=src))
for key,files in firmware.items():
 fw=Path(key).parts[2];comp=Path(key).parts[3]
 manifest=dict(component=comp,container_release=fw,embedded_version='unresolved unless independently established in runtime analysis',status='extracted-bytes-verified',validation_scope='Original extraction proofs; no new behavior, ABI or hardware claims from layout migration',files=files,extraction_registry=os.path.relpath(C+'/manifest.json',key))
 write(key+'/manifest.json',json.dumps(manifest,indent=2)+'\n')
 text=f'# {comp} — {fw}\n\nExtracted firmware binaries. Container release and embedded firmware version are distinct.\n\n'
 text+='\n'.join(f'- [{Path(x["path"]).parent.name} / {Path(x["path"]).name}]({x["path"]})' for x in files)+'\n\n[Identity and status](manifest.json)\n'
 if key==P:text+='\n[Memory layout](memory-layout/README.md) · [Runtime identification](runtime-identification/README.md) · [Command paths](analysis/command-paths.md) · [Receive path](analysis/receive-path.md)\n'
 write(key+'/README.md',text)
write(P+'/memory-layout/layout.json',json.dumps(dict(flash_image=['0x08000000','0x08034f4c'],initial_sp='0x20010000',reset_pointer='0x08004511',vector_base='0x20000000',data_load=['0x080340e8','0x08034f4c'],data_ram=['0x20000400','0x20001264'],bss=['0x20001268','0x2000e414'],gap=['0x20001264','0x20001268'],status='bounded-reset-replay',limitations=['early hardware init and SVC modeled','not a successful boot','gap purpose unresolved']),indent=2)+'\n')
write(P+'/memory-layout/README.md','# NIMH memory layout\n\n[Memory map](layout.json) from the original instruction reset analysis. This establishes initialized-data copying, BSS clearing and SRAM vector placement within the tested reset segment. It does not establish successful boot or free heap.\n\n[Reset replay evidence](../../../../evidence/mixer-13731/nimh-stm32-dice/jobs/command-map-01/startup-replay.json).\n')
write(P+'/runtime-identification/README.md','# NIMH runtime identification\n\neCos/TCAT family identified. Exact eCos vendor revision remains unresolved. The TCAT SDK banner is `1.0.0.0 local beta`; application banner is `1.5.5.0`. Neither identifies the eCos release.\n\n[CLI registrations](cli-registrations.json) · [SDK paths](sdk-source-paths.json) · [Version evidence](version-banner.json)\n\n[Hash-pinned eCos reference](../../../../shared/upstream/ecos/2580ee933ff5bed1f39c18c882f2e1593d980ef6/ecos-source.json). Public reference source is not a complete configured TCAT rebuild.\n')
deliverables=['firmware','memory-layout','runtime-identification','command-paths','receive-path']
write(P+'/manifest.json',json.dumps(dict(component='nimh-stm32-dice',container_release='mixer-13731',embedded_application_version='1.5.5.0',tcat_sdk_version='1.0.0.0 local beta',ecos_revision='unresolved',input_symbol='_ZL13nimh_arm_code',input_sha256='b0979352e18a1093051fc6118a47694773cb9240e88087eca03aaa2ffe0f5e17',deliverables=deliverables,binaries=firmware[P],status='extracted-and-bounded-offline-validated',validation=dict(command_map='../../../../evidence/mixer-13731/nimh-stm32-dice/jobs/command-map-01/validation.json',receive_path='../../../../evidence/mixer-13731/nimh-stm32-dice/jobs/spi-rx-02/validation.json'),limitations=['No original embedded symbol recovery','No reconstructed production C++','No ARM ABI compatibility claim','No hardware timing, concurrency or clock-completion proof']),indent=2)+'\n')
write(C+'/README.md','# Cross-version embedded extraction registry\n\n[Original extraction manifest](manifest.json) records source ELF hashes, original symbols, section mapping, ranges and blob hashes across the analyzed firmware releases.\n\n[Extraction findings](REPORT.md) · [Original Linux verification](linux-verification.json)\n\nThis registry is shared provenance, not owned by mixer-13731/app. Use the component manifests for current binary locations and the layout translation map for old paths.\n')
write('reconstruction/shared/README.md','# Shared reconstruction inputs and references\n\n- `inputs/<SHA-256>/`: original analysis host ELFs; identity independent of component.\n- [Cross-version embedded extraction](extraction/embedded-mcu-01/README.md).\n- [Pinned eCos source provenance](upstream/ecos/2580ee933ff5bed1f39c18c882f2e1593d980ef6/ecos-source.json).\n\nComponent firmware remains discoverable from the version/component artifact index. Shared reference source does not establish a recovered original runtime revision.\n')
write(E+'/README.md','# NIMH evidence\n\nUseful results live in the [component artifact index](../../../artifacts/mixer-13731/nimh-stm32-dice/README.md).\n\n- `jobs/command-map-01/`: logs, native replay fixtures/results, original proof, frozen operators.\n- `jobs/spi-rx-02/`: logs, native receive replay and original proof.\n- `history/`: preserved working trees and earlier indexes.\n- `layout-trial-v2/`: storage migration checks and the previous trial records.\n\nMaintained operators remain at `uc-library/tools/recovery/nimh-command-map/`; copies here record what was used. Historical JSON proof paths are immutable and translated through the layout map.\n')
write(E+'/layout-trial-v2/README.md','# Layout trial v2\n\nThis is storage/migration evidence, not a recovered firmware artifact. All original source files remain. No new archive was created. Only the exact recorded v1 destination files were replaced.\n\n[Layout manifest](manifest.json) · [Useful artifacts](../../../../artifacts/mixer-13731/nimh-stm32-dice/README.md)\n')
write(E+'/layout-trial-v2/manifest.json', '{}\n')
# Navigation audit: generated + current artifact documents must have resolvable local links.
errors=[];links=0
for p in S.rglob('*.md'):
 rel=str(p.relative_to(S))
 if '/history/' in rel or '/prior-layout/' in rel or p.name.startswith('SYMBOLS-before') or '/tracker-fragment' in rel:continue
 for url in re.findall(r'\]\(([^\n]*?)\)',p.read_text()):
  path=urllib.parse.unquote(url.strip('<>').split('#',1)[0])
  if not path or '://' in path:continue
  q=(p.parent/path).resolve()
  if not q.exists():
   # Remainder may refer to immutable original paths outside staged tree.
   try:equiv=R/q.relative_to(S)
   except ValueError:equiv=q
   if not equiv.exists():errors.append((rel,url))
  links+=1
print('NAVIGATION_ERRORS',errors,flush=True)
if errors:raise RuntimeError('Fix stage navigation before install')
# The only removal scope is hash-verified prior copied files and known v1 controls.
for path,h in owned.items():assert sha(R/path)==h
staged=[p for p in S.rglob('*') if p.is_file()]
for p in staged:
 dst=R/p.relative_to(S)
 if dst.exists() and str(dst.relative_to(R)) not in owned:assert sha(dst)==sha(p),('foreign destination collision',dst)
for path in owned:(R/path).unlink()
# Empty directories only; never remove other agents' content.
for p in sorted((R/'reconstruction').rglob('*'),key=lambda x:len(x.parts),reverse=True):
 if p.is_dir():
  try:p.rmdir()
  except OSError:pass
for p in staged:
 dst=R/p.relative_to(S);dst.parent.mkdir(parents=True,exist_ok=True)
 if not dst.exists():shutil.copy2(p,dst)
 assert sha(dst)==sha(p)
# Update only navigation matching this trial's old destinations.
tracker=R/'uc-library/SYMBOLS.md';before=tracker.read_text();after=before
for row in rows:
 src=row['source'];dest=row['destination'];new=MAP[src]
 after=after.replace('../'+dest,'../'+new).replace(str(R/dest),str(R/new))
after=after.replace('../reconstruction/artifacts/mixer-13731/nimh-stm32-dice/migration/README.md','../'+P+'/README.md')
tracker.write_text(after)
translation=[dict(original=x['source'],previous_layout=x['destination'],current=MAP[x['source']],original_sha256=x['source_sha256'],current_sha256=sha(R/MAP[x['source']])) for x in rows]
proof=dict(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='This thread only; storage layout validation, not a behavioral replay',original_files_retained=len(rows),prior_trial_files_replaced=len(owned),files=translation,shared_inputs=[p for p in copied if p.startswith('reconstruction/shared/inputs/')],navigation_links_checked=links,unresolved_historical_fragments=link_audit,deliverables=deliverables,status='passed-layout-only',all_current_files={str(p.relative_to(S)):sha(R/p.relative_to(S)) for p in staged if str(p.relative_to(S))!=E+'/layout-trial-v2/manifest.json'},tracker_sha256=sha(tracker))
newproof=R/E/'layout-trial-v2/manifest.json';newproof.write_text(json.dumps(proof,indent=2)+'\n')
for x in rows:assert sha(R/x['source'])==x['source_sha256']
print('PASS v2 installed:',len(staged),'files;',len(rows),'originals unchanged;',len(owned),'prior trial files replaced;',links,'navigation links checked',flush=True)
print('INDEX',R/P/'README.md',flush=True)
