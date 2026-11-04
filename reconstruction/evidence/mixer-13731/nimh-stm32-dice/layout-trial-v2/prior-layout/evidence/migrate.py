from pathlib import Path
import os,re,json,hashlib,shutil,tarfile,datetime
R=Path.cwd().resolve(); A=R/'.backups/project-root-before-reconstruction.tar'
assert A.exists()
M={}
def put(src,dst):
 src=Path(src);dst=Path(dst)
 if src.is_file() or src.is_symlink():
  assert str(src) not in M or M[str(src)]==str(dst)
  M[str(src)]=str(dst)
def tree(src,dst):
 src=Path(src)
 if not src.exists():return
 for p in sorted(src.rglob('*')):
  if p.is_file() or p.is_symlink():put(p,Path(dst)/p.relative_to(src))
def base(kind,fw,component):return Path('reconstruction')/kind/fw/component
E=Path('evidence/recovery/2026-10-27/xmen-stm32')
manifest=json.loads((E/'manifest.json').read_text())
components={'_ZL13nimh_arm_code':'nimh-stm32-dice','_ZL14nimh_fpga_code':'nimh-fpga-dice','_ZL13noaa_arm_code':'noaa-stm32-dice','_ZL14noaa_fpga_code':'noaa-fpga-dice','_ZL12esa_arm_code':'esa-stm32-dice','_ZL13esa_fpga_code':'esa-fpga-dice','_ZL18dice3_surface_code':'dice3'}
for record in manifest:
 src=record['source'];fw='surface-13840' if src=='Cutter Analysis/surface' else 'mixer-13731' if src=='Cutter Analysis/mixer' else 'mixer-'+re.findall(r'\d+',Path(src).parent.name)[-1]
 for obj in record['objects']:
  p=E/obj['output'];comp=components.get(obj['symbol'],'panel' if 'panel' in obj['symbol'].lower() else 'app')
  put(p,base('artifacts',fw,comp)/'extraction'/Path(obj['output']).parent.name/p.name)
for p in E.rglob('*'):
 if not p.is_file() or str(p) in M:continue
 rel=p.relative_to(E)
 if rel.parts[0]=='inputs':
  fw='surface-13840' if 'surface' in p.name else 'mixer-13731'
  put(p,base('artifacts',fw,'app')/'inputs'/p.name)
 else:
  noisy=p.suffix in ('.log','.pyc','.whl') or p.name.startswith('SYMBOLS-before')
  put(p,base('evidence' if noisy else 'artifacts','mixer-13731','app')/'embedded-extraction'/rel)
for src,job in [('evidence/recovery/2026-10-27/nimh-command-map','command-map'),('evidence/recovery/2026-10-28/nimh-spi-rx','spi-rx')]:
 for p in Path(src).rglob('*'):
  if p.is_file():
   noisy=p.suffix in ('.log','.pyc') or p.name.startswith('SYMBOLS-before')
   put(p,base('evidence' if noisy else 'artifacts','mixer-13731','nimh-stm32-dice')/job/p.relative_to(src))
tree('uc-library/tools/recovery/nimh-command-map',base('artifacts','mixer-13731','nimh-stm32-dice')/'operators/command-map')
tree('uc-library/validation/nimh-command-map',base('evidence','mixer-13731','nimh-stm32-dice')/'legacy-validation-index')
tree('temp/recovery-work/nimh-spi-rx',base('evidence','mixer-13731','nimh-stm32-dice')/'working/spi-rx')
tree('temp/embedded-mcu',base('evidence','mixer-13731','app')/'working/embedded-mcu')
tree('evidence/recovery/2026-10-28/vm-migration/legacy-uc-recovery/nimh-command-map',base('evidence','mixer-13731','nimh-stm32-dice')/'working/legacy-command-map')
# Verify every selected original is archived before copying. Do not follow symlinks.
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source_hash={s:sha(R/s) for s in M if not (R/s).is_symlink()}
backed=set()
with tarfile.open(A,'r:') as tar:
 for item in tar:
  s=item.name.removeprefix('./')
  if s in M:
   if item.isfile():
    h=hashlib.sha256();f=tar.extractfile(item)
    while chunk:=f.read(1024*1024):h.update(chunk)
    assert h.hexdigest()==source_hash[s],('backup mismatch',s)
   else:assert item.issym(),s
   backed.add(s)
assert backed==set(M),('missing from backup',set(M)-backed)
print('Backup verified for',len(backed),'selected originals',flush=True)
records=[]
for s,d in M.items():
 sp=R/s;dp=R/d;dp.parent.mkdir(parents=True,exist_ok=True)
 assert not dp.exists(),('destination already exists',d)
 if sp.is_symlink():os.symlink(os.readlink(sp),dp)
 else:shutil.copy2(sp,dp);assert sha(dp)==source_hash[s]
 records.append(dict(source=s,destination=d,source_sha256=source_hash.get(s),destination_sha256=source_hash.get(s),symlink=sp.is_symlink()))
# Rewrite navigable Markdown links only. Proof/source JSON stays byte-identical.
broken=[];updated=0
for entry in records:
 s=entry['source'];d=entry['destination'];dp=R/d
 if dp.suffix!='.md' or dp.is_symlink():continue
 text=dp.read_text()
 def fix(match):
  nonlocal_dummy=None
  url=match.group(1);angle=url.startswith('<') and url.endswith('>');url=url.strip('<>')
  if '://' in url or url.startswith('#'):return match.group(0)
  path,sep,frag=url.partition('#')
  candidates=[(R/s).parent/path,R/path,Path(path)]
  target=None
  for c in candidates:
   try:key=str(c.resolve().relative_to(R))
   except ValueError:continue
   if key in M:target=R/M[key];break
   if c.exists():target=c.resolve();break
  if target is None:broken.append(dict(file=d,target=url));return match.group(0)
  link=os.path.relpath(target,dp.parent)+(sep+frag if sep else '')
  return ']('+('<'+link+'>' if angle or ' ' in link else link)+')'
 changed=re.sub(r'\]\(([^\n]*?)\)',fix,text)
 if changed!=text:dp.write_text(changed);updated+=1
 entry['destination_sha256']=sha(dp)
 entry['markdown_links_updated']=changed!=text
# Preserve global tracker text, update exact navigation references for these jobs.
tracker=R/'uc-library/SYMBOLS.md';prior=tracker.read_text();current=prior
for s,d in sorted(M.items(),key=lambda x:len(x[0]),reverse=True):
 if s.endswith('.md'):
  current=current.replace(str(R/s),str(R/d)).replace('../'+s,'../'+d)
index=base('artifacts','mixer-13731','nimh-stm32-dice')/'migration'
idx=R/index;idx.mkdir(parents=True,exist_ok=True)
(idx/'SYMBOLS-before.md').write_text(prior)
current+='\nMigration navigation: [STM32 reconstruction index](../reconstruction/artifacts/mixer-13731/nimh-stm32-dice/migration/README.md). Originals retained pending approval.\n'
tracker.write_text(current)
(idx/'README.md').write_text('''# This task’s reconstruction migration

Status: copied and hash-checked; original data retained pending user approval.

- [STM32 command map](../command-map/REPORT.md)
- [STM32 SPI receive results](../spi-rx/REPORT.md)
- [Embedded extraction report](../../app/embedded-extraction/REPORT.md)
- [Migration manifest](manifest.json)

Final job results are under `reconstruction/artifacts/<type>-<version>/<component>/`.
Logs and working notes are under the matching `reconstruction/evidence/` tree.
Extracted blobs retain their original names and container-version identity; this does
not imply embedded firmware shares the host’s application version.

Added components: `noaa-stm32-dice`, `noaa-fpga-dice`, `esa-stm32-dice`,
`esa-fpga-dice`, and `dice3` (surface internal DICE firmware).
The extraction batch’s shared provenance and tools live under mixer-13731/app;
its individual blobs are distributed by original input version/component.
No datasets owned by other agents were migrated.

Historical JSON proofs and scripts retain their original path strings and hashes.
Use manifest.json for path translation; Markdown navigation links were updated in
copies. This migration is a storage/layout check, not a new behavioral validation.

Root backup: `.backups/project-root-before-reconstruction.tar`. Its adjacent log lists
unreadable rootfs files outside this migration. All selected files were individually
verified against the backup before copying. The failed compressed attempt is retained
as `.partial.tar.gz`. No original paths were removed.
''')
# Final verification includes unchanged sources and transformed-copy bindings.
for row in records:
 if not row['symlink']:
  assert sha(R/row['source'])==row['source_sha256']
  assert sha(R/row['destination'])==row['destination_sha256']
proof=dict(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),root=str(R),status='copied-originals-retained-awaiting-approval',
 archive=str(A.relative_to(R)),archive_bytes=A.stat().st_size,backup_all_selected_verified=True,
 root_backup_omission_log='.backups/project-root-before-reconstruction.log',files=records,markdown_files_updated=updated,
 unresolved_markdown_links=broken,originals_deleted=0,other_agent_folders_migrated=0)
(idx/'manifest.json').write_text(json.dumps(proof,indent=2)+'\n')
print('COPIED',len(records),'files; Markdown updated',updated,'unresolved links',len(broken),flush=True)
print('INDEX',idx/'README.md',flush=True)
