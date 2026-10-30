"""Build pinned reference libraries in project temp; preserve vendor checkouts."""
from pathlib import Path
import os,json,hashlib,subprocess,shutil
r=Path.cwd();lib=r/'uc-library';work=r/'temp/recovery-work/hal-oss-providers';out=r/'evidence/recovery/2026-10-29/surface-hal-priority/oss-reference-build-01';out.mkdir(parents=True,exist_ok=False);work.mkdir(parents=True,exist_ok=False);scratch=work/'tmp';scratch.mkdir();env=dict(os.environ,TMPDIR=str(scratch),TMP=str(scratch),TEMP=str(scratch));cmake=lib/'.venv/bin/cmake';ctest=lib/'.venv/bin/ctest';prefix=work/'sdk';commands=[];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();pins=json.loads((lib/'validation/hal-oss-source-references.json').read_text())['references']
def run(name,cmd):
 command=list(map(str,cmd));p=subprocess.run(command,cwd=r,env=env,text=True,capture_output=True);(out/(name+'.stdout')).write_text(p.stdout);(out/(name+'.stderr')).write_text(p.stderr);commands.append(dict(name=name,command=command,returncode=p.returncode));(out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');assert p.returncode==0,p.stderr[-2000:]
for pin in pins:
 src=r/pin['reference_checkout'];dst=work/(pin['name']+'-source');shutil.copytree(src,dst,ignore=shutil.ignore_patterns('.git'));b=work/(pin['name']+'-build');options=['-DCMAKE_POLICY_VERSION_MINIMUM=3.5','-DCMAKE_BUILD_TYPE=Release','-DCMAKE_INSTALL_PREFIX='+str(prefix)]
 if pin['name']=='libpng':options+=['-DZLIB_LIBRARY='+str(prefix/'lib/libz.a'),'-DZLIB_INCLUDE_DIR='+str(prefix/'include'),'-DPNG_SHARED=ON','-DPNG_STATIC=ON','-DPNG_TESTS=ON']
 run(pin['name']+'-configure',[cmake,'-S',dst,'-B',b,*options]);run(pin['name']+'-build',[cmake,'--build',b,'-j','2']);run(pin['name']+'-tests',[ctest,'--test-dir',b,'--output-on-failure']);run(pin['name']+'-install',[cmake,'--install',b])
 # Verify original tracked source remains byte-identical; source-copy changes stay temporary.
 manifest=json.loads((r/'evidence/recovery/2026-10-29/surface-hal-priority/oss-source-pins'/(pin['name']+'.json')).read_text())['tracked_files']
 for n,row in manifest.items():
  p=src/n;data=os.readlink(p).encode() if p.is_symlink() else p.read_bytes();assert hashlib.sha256(data).hexdigest()==row['sha256'],n
artifacts={str(p.relative_to(r)):sha(p) for p in prefix.rglob('*') if p.is_file() and not p.is_symlink()};(out/'validation.json').write_text(json.dumps(dict(passed=True,source_pins=pins,artifacts=artifacts,commands=commands,source_checkouts_unmodified=True,active_project_build_changed=False,scope='Official source-built reference providers and upstream tests only. Source/API/behavior binding to recovered HAL remains separate; no original binary/ARM ABI equivalence claimed.'),indent=2)+'\n');print(json.dumps({'passed':True,'artifacts':len(artifacts)}))
