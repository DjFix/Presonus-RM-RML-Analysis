"""Seal this bounded checkpoint with all unresolved mappings explicit."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil,tarfile,subprocess,platform
ROOT=Path('/home/rs/projects/opencs/ai-line-analysis');OP=ROOT/'uc-library/tools/recovery/nimh-bus-04'
B=ROOT/'evidence/recovery/2026-10-27/nimh-bus-04';OLD=ROOT/'evidence/recovery/2026-10-27/nimh-functional-03'
UP=ROOT/'temp/fpga-combine/upstream'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1048576),b''):h.update(c)
    return h.hexdigest()
save=lambda n,v:(B/n).write_text(json.dumps(v,indent=2)+'\n')
revision=subprocess.check_output(['git','-C',str(UP),'rev-parse','HEAD'],text=True).strip()
assert revision=='01bdbb674f784740f977327b2edfe099ebf63ae0'
assert not subprocess.check_output(['git','-C',str(UP),'status','--porcelain'],text=True).strip()
dbsha=sha(UP/'databases/spartan6.zstd');assert dbsha=='e44e5f9a7075854d653dc1bbb987ed9fe2a63098fcc5aee2a26521cf7f52ad10'
for n in ['functional-audit.json','bus-model-audit.json','bram-model-audit.json']:
    a=json.loads((B/n).read_text());assert a.get('passed',a.get('complete_replay_passed'))
commands=json.loads((B/'commands.json').read_text())
y=[r for r in commands if r['step']=='yosys'][-1]
assert y['returncode']==0 and y['verilog_sha256']==sha(B/'functional-partial.v')
assert all(r['returncode']==0 for r in commands)
assert (B/'REPORT.md').exists()
src=B/'source';src.mkdir(exist_ok=True)
for p in OP.glob('*.py'):shutil.copyfile(p,src/p.name)
shutil.copytree(OP/'docs',src/'docs',dirs_exist_ok=True)
deps=B/'dependencies';deps.mkdir(exist_ok=True)
for n in ['evidence-manifest.json','pins.json','physical-interface-pins.json','stm32-mmio-accesses.json','avb-register-map.json','ins-register-map.json']:
    shutil.copyfile(OLD/n,deps/('phase03-'+n))
for n in ['yosys-version.txt','yosys-packages.txt']:shutil.copyfile(OLD/n,B/n)
prev=ROOT/'evidence/recovery/2026-10-27/nimh-fpga-connectivity-02'
for n in ['xmen_nimh_avb_top.bin','primitive-settings.jsonl']:shutil.copyfile(prev/'dependencies'/n,deps/n)
pins=json.loads((OLD/'pins.json').read_text())
save('pins.json',dict(project_combine_revision=revision,database_sha256=dbsha,vendor_tree_clean=True,
  bitstream_sha256=sha(deps/'xmen_nimh_avb_top.bin'),stm32_sha256=pins['stm32_sha256'],input_elf_sha256=pins['input_elf_sha256'],
  parent_manifest_sha256=sha(OLD/'evidence-manifest.json'),parent_archive_sha256=sha(OLD/'functional-exports.tar.gz'),
  python=platform.python_version(),yosys=(B/'yosys-version.txt').read_text().strip(),
  operator_sources={p.name:sha(p) for p in sorted(src.glob('*.py'))},
  scope=dict(raw_equation_replay=True,counter_exhaustive=True,ram_content_bounded=True,hdl_parse_hierarchy=True,
    named_bank_attribution_complete=False,transaction_reachability=False,hardware=False,cpp_readiness=False)))
save('model.json',dict(phase='nimh-bus-04',report='REPORT.md',equations='functional-equations.jsonl',verilog='functional-partial.v',
  storage_sidecar='bram-storage-models.json',conditional_groups='conditional-register-groups.json',bank_candidates='register-bank-cones.json',
  exact_cell_cones='conditional-cell-cones.jsonl',consumers='register-datapath-consumers.json',
  unresolved=['Unique AVB/PTP/audio bank assignment','Transaction-state reachability and byte assembly','Data lane permutation and aperture selects','DSP/SRL/DDR/clock and RAM pipeline behavior','Two HCLK bits'],
  reproduction='Operator sources require the hash-pinned preceding phases at their recorded project paths. RAM behavior is a sidecar, not integrated into flat HDL.'))
excluded={'evidence-manifest.json','bus-exports.tar.gz','mirror-audit.json','seal.log','payload-files.json'}
files={str(p.relative_to(B)):dict(sha256=sha(p),bytes=p.stat().st_size) for p in sorted(B.rglob('*')) if p.is_file() and str(p.relative_to(B)) not in excluded}
save('payload-files.json',dict(files=files))
files['payload-files.json']=dict(sha256=sha(B/'payload-files.json'),bytes=(B/'payload-files.json').stat().st_size)
archive=B/'bus-exports.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
    for n in files:tar.add(B/n,arcname=n,recursive=False)
files[archive.name]=dict(sha256=sha(archive),bytes=archive.stat().st_size)
save('evidence-manifest.json',dict(created_at=datetime.now(timezone.utc).isoformat(),files=files,
  scope='Bounded bus/primitive recovery and conditional cell cones. Named-bank attribution remains unresolved. No hardware or readiness promotion.'))
print('Sealed',len(files),'files; archive',archive.stat().st_size,'bytes; SHA256',sha(archive))
