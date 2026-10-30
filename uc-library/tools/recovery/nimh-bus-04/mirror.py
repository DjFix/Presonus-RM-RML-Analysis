from pathlib import Path
import hashlib,json,tarfile,sys
remote='--remote-close' in sys.argv
ROOT=Path('/home/rs/projects/opencs/ai-line-analysis' if remote else '/home/rs/projects/opencs/ai-line-analysis')
B=ROOT/'evidence/recovery/2026-10-27/nimh-bus-04'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1048576),b''):h.update(c)
    return h.hexdigest()
manifest=json.loads((B/'evidence-manifest.json').read_text())
for n,r in manifest['files'].items():assert sha(B/n)==r['sha256'],n
if not remote:
    names=set()
    with tarfile.open(B/'bus-exports.tar.gz','r|gz') as tar:
        for member in tar:
            assert member.isfile();h=hashlib.sha256();f=tar.extractfile(member)
            for c in iter(lambda:f.read(1048576),b''):h.update(c)
            assert h.hexdigest()==manifest['files'][member.name]['sha256'],member.name
            names.add(member.name)
    assert names==set(manifest['files'])-{'bus-exports.tar.gz'}
    proof=dict(passed=True,checked_files=len(manifest['files']),archive_members_checked=len(names),
      evidence_manifest_sha256=sha(B/'evidence-manifest.json'),archive_sha256=sha(B/'bus-exports.tar.gz'))
    (B/'mirror-audit.json').write_text(json.dumps(proof,indent=2)+'\n')
else:
    proof=json.loads((B/'mirror-audit.json').read_text());assert proof['passed']
    assert proof['evidence_manifest_sha256']==sha(B/'evidence-manifest.json')
    assert proof['archive_sha256']==sha(B/'bus-exports.tar.gz')
lib=ROOT/('uc-library' if remote else 'uc-library')
v=lib/'validation/nimh-bus-04';v.mkdir(parents=True,exist_ok=True)
summary=dict(phase='nimh-bus-04',pins=json.loads((B/'pins.json').read_text()),
  coverage=json.loads((B/'functional-coverage.json').read_text()),register_maps=json.loads((B/'register-map-coverage.json').read_text()),
  bus_audit=json.loads((B/'bus-model-audit.json').read_text()),mirror=proof,cpp_readiness=False,hardware_validation=False)
(v/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
heading='## NIMH FPGA bus and conditional register cones — 2026-10-28'
fragment=f'''\n\n{heading}

Original mixer-13731 FPGA `_ZL14nimh_fpga_code` and STM32 `_ZL13nimh_arm_code`; input ELF SHA-256 `9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07`.

| Layer | Status and bounded coverage |
|---|---|
| Bus structure | Sixteen shared-tristate data pads, H3 clock, two 14-bit address counters; data permutation and exact control roles unresolved |
| Primitive behavior | 108 I/O FFs; auxiliary mixed-width RAM models for 86 logical groups; RAM pipeline/collision, DSP/SRL/DDR gaps retained |
| Physical cones | 2,984 conditional cells, 307 enable groups, 21,398 first consumer edges; all sixteen readback paths exported |
| Named bank attribution | 0/11 uniquely admitted bank regions; aliased candidates and history qualifiers preserved, no complete AVB/PTP/audio map claimed |
| Linux validation | Equation replay, exhaustive counter/tristate checks, bounded RAM checks and full HDL parse/hierarchy passed |
| C++ / hardware | No readiness promotion and no hardware validation |

[Report, exact cell identities and remaining gaps]({B/'REPORT.md'}). The initial thirteen-bit counter interpretation was corrected before sealing by excluding carry-chain state from external controls; final counters are fourteen bits.
'''
(v/'tracker-fragment.md').write_text(fragment)
tracker=lib/'SYMBOLS.md';text=tracker.read_text()
if heading not in text:
    (v/'SYMBOLS-before.md').write_text(text);tracker.write_text(text+fragment)
else:assert fragment in text
print('Mirror hashes verified:',proof['checked_files'],'files; tracker:',tracker)
