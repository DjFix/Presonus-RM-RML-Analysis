"""Seal the pinned connectivity phase and its self-contained data archive."""
from pathlib import Path
import hashlib,json,shutil,subprocess,tarfile,datetime

ROOT=Path('/home/rs/projects/opencs/ai-line-analysis')
OUT=ROOT/'evidence/recovery/2026-10-27/nimh-fpga-connectivity-02'
OLD=ROOT/'evidence/recovery/2026-10-27/nimh-fpga-decode-01'
UP=ROOT/'temp/fpga-combine/upstream'
SRC=ROOT/'uc-library/tools/recovery/nimh-fpga-connectivity-02'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def git(*a):return subprocess.check_output(['git','-C',str(UP),*a],text=True).strip()
assert git('rev-parse','HEAD')=='01bdbb674f784740f977327b2edfe099ebf63ae0'
assert not git('status','--porcelain')
assert sha(UP/'databases/spartan6.zstd')=='e44e5f9a7075854d653dc1bbb987ed9fe2a63098fcc5aee2a26521cf7f52ad10'
assert json.loads((OUT/'graph-audit.json').read_text())['passed']
cmd=['/snap/bin/cargo','fmt','--manifest-path',str(SRC/'Cargo.toml'),'--check']
p=subprocess.run(cmd,capture_output=True,text=True)
(OUT/'format-check.log').write_text('COMMAND '+repr(cmd)+'\n'+p.stdout+p.stderr+'\nEXIT '+str(p.returncode)+'\n')
assert p.returncode==0
source=OUT/'source';source.mkdir(exist_ok=True)
source_hashes={}
for name in ['Cargo.toml','Cargo.lock','src/main.rs','src/bin/inspect_fields.rs','analyze_graph.py','audit_graph.py','seal.py']:
 p=SRC/name;q=source/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q);source_hashes[name]=sha(p)
dep=OUT/'dependencies';dep.mkdir(exist_ok=True)
for source_file,name in [
 (OLD/'decoded-final/primitive-settings.jsonl','primitive-settings.jsonl'),
 (ROOT/'evidence/recovery/2026-10-27/fpga-identification/mixer-13731/xmen_nimh_avb_top.bin','xmen_nimh_avb_top.bin'),
 (UP/'databases/spartan6.zstd','spartan6.zstd'),
 (UP/'LICENSE-0BSD.txt','LICENSE-0BSD.txt'),(UP/'LICENSE-Apache-2.0.txt','LICENSE-Apache-2.0.txt')]:
 shutil.copyfile(source_file,dep/name)
assert sha(dep/'xmen_nimh_avb_top.bin')=='945b2c3a0f74cd39825ec361da680c92303f20ac7f7a98756b7a829216ef9dbb'
shutil.copyfile(OLD/'input-identity.json',OUT/'input-identity.json')
excerpts=[]
for name,start,end in [
 ('re/xilinx/ise-hammer/src/spartan6/dcm.rs',940,965),
 ('re/xilinx/ise-hammer/src/spartan6/misc.rs',858,878),
 ('re/xilinx/rdverify/spartan6/src/lib.rs',98,168),
 ('re/xilinx/rdverify/spartan6/src/lib.rs',169,250),
 ('re/xilinx/rdverify/spartan6/src/lib.rs',434,470),
 ('public/spartan6/src/expand.rs',530,558),
 ('public/spartan6/src/expand.rs',605,640),
 ('public/spartan6/src/defs.rs',2504,2527)]:
 p=UP/name;excerpts.append(dict(path=name,start=start,end=end,source_sha256=sha(p),text='\n'.join(p.read_text().splitlines()[start-1:end])))
(OUT/'investigation/source-excerpts.json').write_text(json.dumps(excerpts,indent=2)+'\n')
pins=dict(commit=git('rev-parse','HEAD'),upstream_url='https://codeberg.org/prjunnamed/prjcombine.git',upstream_status=git('status','--porcelain'),
 database_sha256=sha(UP/'databases/spartan6.zstd'),database_git_blob=git('rev-parse','HEAD:databases/spartan6.zstd'),
 source_sha256=source_hashes,binary_sha256={name:sha(ROOT/'temp/fpga-combine/target/release'/name) for name in ['presonus-nimh-connectivity','inspect_fields']},
 previous_evidence_manifest_sha256=sha(OLD/'evidence-manifest.json'),
 rustc=subprocess.check_output(['/snap/bin/rustc','--version'],text=True).strip(),cargo=subprocess.check_output(['/snap/bin/cargo','--version'],text=True).strip())
(OUT/'pins.json').write_text(json.dumps(pins,indent=2)+'\n')
netlist=json.loads((OUT/'netlist.json').read_text())
netlist.update(archive='connectivity-exports.tar.gz',primitive_settings_in_archive='dependencies/primitive-settings.jsonl',raw_bitstream_in_archive='dependencies/xmen_nimh_avb_top.bin',pinned_database_in_archive='dependencies/spartan6.zstd')
(OUT/'netlist.json').write_text(json.dumps(netlist,indent=2)+'\n')
# Include all data needed to consume the graph, plus small explanatory records.
names=['export','dependencies','investigation','net-status.jsonl','input-pin-net-status.jsonl','source-bindings.jsonl','driver-signatures.i32le','driver-polarities.u8','unresolved-nets.csv','REPORT.md']
names+=sorted(p.name for p in OUT.glob('*.json') if p.name not in ('evidence-manifest.json','mirror-audit.json'))
with tarfile.open(OUT/'connectivity-exports.tar.gz','w:gz',compresslevel=6) as tar:
 for name in names:tar.add(OUT/name,arcname=name,recursive=True)
files={}
for p in sorted(OUT.rglob('*')):
 if not p.is_file() or p.is_symlink() or p.name in ('evidence-manifest.json','seal.log','mirror-audit.json'):continue
 files[str(p.relative_to(OUT))]=dict(size=p.stat().st_size,sha256=sha(p))
(OUT/'evidence-manifest.json').write_text(json.dumps(dict(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=files,
 scope='All phase artifacts except this manifest, the live seal log and the subsequent mirror audit.'),indent=2)+'\n')
print('Sealed',len(files),'files. Archive bytes:',(OUT/'connectivity-exports.tar.gz').stat().st_size)
print('Source commit',pins['commit'],'database',pins['database_sha256'])
