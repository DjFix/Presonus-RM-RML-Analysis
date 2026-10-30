"""Seal bounded FPGA/MCU analysis evidence; no readiness or hardware admission."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil,subprocess,tarfile,platform
import capstone
ROOT=Path('/home/rs/projects/opencs/ai-line-analysis')
OP=ROOT/'uc-library/tools/recovery/nimh-functional-03'
B=ROOT/'evidence/recovery/2026-10-27/nimh-functional-03'
PREV=ROOT/'evidence/recovery/2026-10-27/nimh-fpga-connectivity-02'
UP=ROOT/'temp/fpga-combine/upstream'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
    return h.hexdigest()
def save(n,v):(B/n).write_text(json.dumps(v,indent=2)+'\n')
assert subprocess.check_output(['git','-C',str(UP),'rev-parse','HEAD'],text=True).strip()=='01bdbb674f784740f977327b2edfe099ebf63ae0'
assert not subprocess.check_output(['git','-C',str(UP),'status','--porcelain'],text=True).strip()
assert sha(UP/'databases/spartan6.zstd')=='e44e5f9a7075854d653dc1bbb987ed9fe2a63098fcc5aee2a26521cf7f52ad10'
commands=json.loads((B/'commands.json').read_text())
y=[r for r in commands if r['step']=='yosys'][-1]
assert y['returncode']==0 and '; proc;' not in y['command'][-1]
assert y['verilog_sha256']==sha(B/'functional-partial.v')
audit=json.loads((B/'functional-audit.json').read_text())
assert audit['passed_within_evaluated_domain']
assert audit['complete_replay_passed']
for n in ['functional-feedback-components.json','avb-register-map.json','ins-register-map.json','REPORT.md']:assert (B/n).exists()
src=B/'source';src.mkdir(exist_ok=True)
for p in OP.glob('*.py'):shutil.copyfile(p,src/p.name)
deps=B/'dependencies';deps.mkdir(exist_ok=True)
fw=ROOT/'evidence/recovery/2026-10-27/xmen-stm32/images/mixer-analysis/_ZL13nimh_arm_code.bin'
assert sha(fw)=='b0979352e18a1093051fc6118a47694773cb9240e88087eca03aaa2ffe0f5e17'
shutil.copyfile(fw,deps/fw.name)
for n in ['xmen_nimh_avb_top.bin','primitive-settings.jsonl']:
    shutil.copyfile(PREV/'dependencies'/n,deps/n)
shutil.copyfile(PREV/'netlist.json',deps/'input-netlist.json')
shutil.copyfile(PREV/'evidence-manifest.json',deps/'connectivity-evidence-manifest.json')
docs=json.loads((OP/'inputs/docs/manifest.json').read_text())
(deps/'docs').mkdir(exist_ok=True)
for r in docs:
    p=ROOT/r['path'];assert sha(p)==r['sha256']
    shutil.copyfile(p,deps/'docs'/p.name)
save('dependencies/docs-manifest.json',docs)
save('dependencies/official-web-references.json',[
 dict(url='https://www.st.com/resource/en/reference_manual/rm0008-stm32f103xx-advanced-armbased-32bit-mcus-stmicroelectronics.pdf',
      checked='2026-10-27',observation='Official indexed RM0008: BCR MWID bits5:4 = 01 selects16bits; MUXEN0 selects nonmultiplexed bus.',
      local_download='Initial long-name URL timed out. No local RM0008 PDF claimed.'),
 dict(url='https://docs.amd.com/v/u/en-US/ug384',checked='2026-10-27',local_copy='docs/UG384.pdf')])
save('pins.json',dict(project_combine_revision='01bdbb674f784740f977327b2edfe099ebf63ae0',
    database_sha256=sha(UP/'databases/spartan6.zstd'),vendor_tree_clean=True,
    parent_evidence_manifest_sha256=sha(PREV/'evidence-manifest.json'),parent_archive_sha256=sha(PREV/'connectivity-exports.tar.gz'),
    bitstream_sha256=sha(deps/'xmen_nimh_avb_top.bin'),stm32_sha256=sha(fw),
    input_elf_sha256='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07',
    stm32_original_symbol='_ZL13nimh_arm_code',stm32_elf_va='0x2608d7',stm32_elf_file_offset='0x2588d7',
    python=platform.python_version(),capstone=capstone.__version__,
    yosys=(B/'yosys-version.txt').read_text().strip(),yosys_packages=(B/'yosys-packages.txt').read_text().splitlines(),
    operator_sources={p.name:sha(p) for p in sorted(src.glob('*.py'))},
    validation_scope=dict(bounded_equation_replay=True,complete_replay=audit['complete_replay_passed'],
      full_verilog_parse_hierarchy=True,whole_design_synthesis=False,formal_equivalence=False,hardware=False,cpp_readiness=False)))
save('model.json',dict(format='presonus-nimh-partial-functional-v1',
    files=dict(verilog='functional-partial.v',equations='functional-equations.jsonl',raw_equations='physical-equations.jsonl',
        boundaries='functional-boundaries.json',port_map='verilog-port-map.json',block_assessment='block-assessment.json',
        coverage='functional-coverage.json',audit='functional-audit.json',pins='pins.json'),
    assumptions=['Abstract GAP input values are supplied independently by the analysis harness.',
      'No hard-block, clock/jitter, I/O timing or hardware equivalence is established.',
      'IOB input inversion, directed route polarity, decoded LUT/register/carry settings are preserved.',
      'Original HDL names/hierarchy and precise board signal assignments remain unresolved.']))
archive=B/'functional-exports.tar.gz'
excluded={'evidence-manifest.json','functional-exports.tar.gz','mirror-audit.json','seal.log','payload-files.json'}
files={str(p.relative_to(B)):dict(sha256=sha(p),bytes=p.stat().st_size) for p in sorted(B.rglob('*'))
       if p.is_file() and str(p.relative_to(B)) not in excluded}
save('payload-files.json',dict(files=files))
files['payload-files.json']=dict(sha256=sha(B/'payload-files.json'),bytes=(B/'payload-files.json').stat().st_size)
with tarfile.open(archive,'w:gz') as tar:
    for n in files:tar.add(B/n,arcname=n,recursive=False)
files[archive.name]=dict(sha256=sha(archive),bytes=archive.stat().st_size)
save('evidence-manifest.json',dict(created_at=datetime.now(timezone.utc).isoformat(),files=files,
    scope='Bounded partial functional recovery. Explicit primitive/feedback gaps; no full-equivalence or hardware claim.'))
print('Sealed files:',len(files),'archive bytes:',archive.stat().st_size,'archive SHA256:',sha(archive))
