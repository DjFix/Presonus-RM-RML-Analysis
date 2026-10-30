"""Preserve reproducible decoder inputs, final exports and evidence hashes."""
from pathlib import Path
import datetime
import hashlib
import json
import shutil
import subprocess
import tarfile

root=Path('/home/rs/projects/opencs/ai-line-analysis')
out=root/'evidence/recovery/2026-10-27/nimh-fpga-decode-01'
up=root/'temp/fpga-combine/upstream'
adapter=root/'uc-library/tools/recovery/nimh-fpga-decode-01'

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()

def git(*args):
    return subprocess.check_output(['git','-C',str(up),*args],text=True).strip()

assert git('rev-parse','HEAD')=='01bdbb674f784740f977327b2edfe099ebf63ae0'
assert not git('status','--porcelain')
if (out/'pins.json').exists() and not (out/'pins-initial.json').exists():
    shutil.copyfile(out/'pins.json',out/'pins-initial.json')
if (out/'source').exists() and not (out/'source-initial').exists():
    (out/'source').rename(out/'source-initial')
source=out/'source'
source.mkdir(exist_ok=True)
pins=dict(upstream_url='https://codeberg.org/prjunnamed/prjcombine.git',
          commit=git('rev-parse','HEAD'),upstream_status=git('status','--porcelain'),files={})
for name in ['databases/spartan6.zstd','databases/spartan6.txt','public/spartan6/src/bitstream/parse.rs','public/virtex2/src/bitstream/packet_s3a.rs']:
    pins['files'][name]=dict(sha256=sha(up/name),git_blob=git('rev-parse','HEAD:'+name))
for name in ['Cargo.toml','Cargo.lock','src/main.rs','summarize.py','seal.py']:
    p=adapter/name
    target=source/name
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(p,target)
    pins['files']['adapter/'+name]=dict(sha256=sha(p))
db=out/'pinned-db'
db.mkdir(exist_ok=True)
for name in ['spartan6.zstd','spartan6.txt']:
    shutil.copyfile(up/'databases'/name,db/name)
for name in ['LICENSE-0BSD.txt','LICENSE-Apache-2.0.txt']:
    shutil.copyfile(up/name,db/name)
pins['binary_sha256']=sha(root/'temp/fpga-combine/target/release/presonus-nimh-decode')
pins['rustc']=subprocess.check_output(['/snap/bin/rustc','--version'],text=True).strip()
pins['cargo']=subprocess.check_output(['/snap/bin/cargo','--version'],text=True).strip()
pins['rustfmt']=subprocess.check_output(['/snap/bin/cargo','fmt','--version'],text=True).strip()
(out/'pins.json').write_text(json.dumps(pins,indent=2)+'\n')
cmd=['/snap/bin/cargo','fmt','--manifest-path',str(adapter/'Cargo.toml'),'--check']
p=subprocess.run(cmd,capture_output=True,text=True)
(out/'format-check.log').write_text('COMMAND '+repr(cmd)+'\n'+p.stdout+p.stderr+'\nEXIT '+str(p.returncode)+'\n')
assert p.returncode==0
identity=json.loads((root/'evidence/recovery/2026-10-27/fpga-identification/manifest.json').read_text())
elf=next(e for e in identity['inputs'] if 'mixer' in e['input'])
image=next(i for i in elf['images'] if i['mangled']=='_ZL14nimh_fpga_code')
(out/'input-identity.json').write_text(json.dumps(dict(elf_sha256=elf['elf_sha256'],firmware_version=13731,**image),indent=2)+'\n')
log=(out/'decode-final.log').read_text()
assert 'panic' not in log.lower() and 'mismatch' not in log.lower()
checks=dict(format_check='passed',frame_byte_audit=json.loads((out/'frame-byte-audit.json').read_text())['status'],
            crc_mismatch_diagnostics=0,crc_scope='No mismatch diagnostics from the pinned parser; byte audit is independent of its CRC implementation.',
            hardware_actions=0,global_netlist=False,semantic_validation=False)
(out/'checks.json').write_text(json.dumps(checks,indent=2)+'\n')
with tarfile.open(out/'final-exports.tar.gz','w:gz',compresslevel=6) as tar:
    for p in sorted((out/'decoded-final').iterdir()):
        assert p.is_file() and not p.is_symlink()
        tar.add(p,arcname='decoded-final/'+p.name,recursive=False)
files={}
for p in sorted(out.rglob('*')):
    relative=p.relative_to(out)
    if not p.is_file() or p.is_symlink() or p.name in ('evidence-manifest.json','seal.log'):
        continue
    if relative.parts[0] in ('decoded','source-initial'):
        continue
    files[str(relative)]=dict(size=p.stat().st_size,sha256=sha(p))
(out/'evidence-manifest.json').write_text(json.dumps(dict(
    created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    files=files,scope='Final exports and supporting proofs; live seal.log excluded from its own seal. Initial decode/source retained separately on VM101.'),indent=2)+'\n')
print('Sealed',len(files),'files; archive bytes',(out/'final-exports.tar.gz').stat().st_size)
print('Final adapter SHA-256',pins['files']['adapter/src/main.rs']['sha256'])
print('Database SHA-256',pins['files']['databases/spartan6.zstd']['sha256'])
