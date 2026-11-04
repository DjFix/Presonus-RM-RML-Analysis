from pathlib import Path
import json,re,os,hashlib,shutil
R=Path.cwd().resolve();D=R/'reconstruction/artifacts/mixer-13731/nimh-stm32-dice/migration';P=D/'manifest.json';m=json.loads(P.read_text());mapping={r['source']:r['destination'] for r in m['files']};historical=[];missing=[];checked=0
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for row in m['files']:
 src=R/row['source'];dst=R/row['destination']
 if dst.suffix!='.md':continue
 if dst.name.startswith('SYMBOLS-before'):
  shutil.copy2(src,dst);row['destination_sha256']=sha(dst);row['markdown_links_updated']=False
  historical.append(row['destination']);continue
 def fix(x):
  url=x.group(1).strip('<>')
  if '://' in url or url.startswith('#'):return x.group(0)
  url,sep,frag=url.partition('#')
  target=None
  for candidate in [(dst.parent/url),(src.parent/url),(R/'uc-library'/url),(R/url)]:
   try:key=str(candidate.resolve().relative_to(R))
   except ValueError:continue
   if key in mapping:target=R/mapping[key];break
   if candidate.exists():target=candidate.resolve();break
  if target is None:missing.append(dict(file=row['destination'],target=url));return x.group(0)
  link=os.path.relpath(target,dst.parent)+(sep+frag if sep else '')
  return '](<'+link+'>)' if ' ' in link else ']('+link+')'
 text=dst.read_text();new=re.sub(r'\]\(([^\n]*?)\)',fix,text)
 if new!=text:dst.write_text(new)
 row['destination_sha256']=sha(dst);row['markdown_links_updated']=sha(dst)!=row['source_sha256'];checked+=1
E=R/'reconstruction/evidence/mixer-13731/nimh-stm32-dice/migration';E.mkdir(parents=True,exist_ok=True)
shutil.move(D/'SYMBOLS-before.md',E/'SYMBOLS-before.md')
for f in ['migrate.py','finalize.py']:shutil.copy2(R/'temp/recovery-work/nimh-layout-migration'/f,E/f)
shutil.copy2(R/'.backups/project-root-before-reconstruction.log',E/'root-backup-omissions.log')
shutil.copy2(R/'.backups/nimh-layout-migration.log',E/'migration.log')
m['historical_snapshot_files_preserved']=historical;m['unresolved_markdown_links']=missing;m['navigation_markdown_files_checked']=checked
m['backup_omission_warnings']=(E/'root-backup-omissions.log').read_text().splitlines()
m['migration_support_files']={str(p.relative_to(R)):sha(p) for p in E.iterdir() if p.is_file()}
for row in m['files']:
 if not row['symlink']:
  assert sha(R/row['source'])==row['source_sha256'],row['source']
  assert sha(R/row['destination'])==row['destination_sha256'],row['destination']
P.write_text(json.dumps(m,indent=2)+'\n')
# Verify new index links as well.
for p in [D/'README.md']:
 for url in re.findall(r'\]\(([^\n]*?)\)',p.read_text()):assert (p.parent/url.strip('<>')).exists(),url
print('PASS: original hashes retained, copied hashes checked, index links resolve.')
print('Current navigation files:',checked,'historical snapshots:',len(historical),'unresolved current links:',len(missing))
for x in missing:print(x)
print('Backup warnings:',len(m['backup_omission_warnings']))
