"""Verify official source-reference checkouts and preserve every tracked blob."""
from pathlib import Path
import json,hashlib,subprocess,os
r=Path.cwd();out=r/'evidence/recovery/2026-10-29/surface-hal-priority/oss-source-pins';out.mkdir(parents=True,exist_ok=False);records=[]
for name,folder,url,tag,commit,licenses in [('zlib','zlib-reference-1.2.11','https://github.com/madler/zlib.git','v1.2.11','cacf7f1d4e3d44d871b605da3b647f07d718623f',['README','zlib.h']),('libpng','libpng-reference-1.6.10','https://github.com/pnggroup/libpng.git','v1.6.10','4df37bfa4f79dcd742fca6155e26b8d37b591c30',['LICENSE','png.h'])]:
 root=r/'third_party'/folder
 def git(*args):return subprocess.check_output(['git','-C',str(root),*args])
 head=git('rev-parse','HEAD').decode().strip();assert head==commit and git('rev-parse',tag+'^{commit}').decode().strip()==commit;assert git('remote','get-url','origin').decode().strip()==url;files={}
 for row in git('ls-tree','-r','-z','HEAD').split(b'\0'):
  if not row:continue
  meta,path=row.split(b'\t',1);mode,kind,blob=meta.decode().split();path=path.decode();p=root/path;assert kind=='blob',path;data=os.readlink(p).encode() if mode=='120000' else p.read_bytes();actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest();assert actual==blob,path;files[path]=dict(git_blob=blob,sha256=hashlib.sha256(data).hexdigest(),size=len(data),mode=mode)
 notices={n:files[n] for n in licenses};record=dict(name=name,reference_checkout=str(root.relative_to(r)),official_repository=url,tag=tag,tag_object=git('rev-parse',tag).decode().strip(),tag_object_type=git('cat-file','-t',tag).decode().strip(),commit=commit,tree=git('rev-parse','HEAD^{tree}').decode().strip(),license_notices=notices,tracked_files=files,all_worktree_blobs_match_git=True,source_reference_only=True,active_build_changed=False,version_evidence='evidence/recovery/2026-10-29/surface-hal-priority/oss-version-string-leads.json',scope='Official source available for reuse; binary patches/configuration/API equivalence not established by version strings or matching C names.')
 (out/(name+'.json')).write_text(json.dumps(record,indent=2)+'\n');records.append({k:v for k,v in record.items() if k!='tracked_files'})
(r/'uc-library/validation/hal-oss-source-references.json').write_text(json.dumps({'references':records,'no_binary_vendor_reconstruction':True,'production_source_provider':'Current CCL provider still uses existing real systemlibpng/zlib; reference APIs/configuration comparison precedes any provider replacement.'},indent=2)+'\n');print(json.dumps([{'name':x['name'],'commit':x['commit'],'license_files':list(x['license_notices'])} for x in records]))
