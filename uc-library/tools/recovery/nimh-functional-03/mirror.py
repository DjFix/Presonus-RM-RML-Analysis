"""Audit the local mirror and append a scoped tracker entry on either project host."""
from pathlib import Path
import hashlib,json,tarfile,sys
LOCAL=Path('/home/rs/projects/opencs/ai-line-analysis')
REMOTE=Path('/home/rs/projects/opencs/ai-line-analysis')
remote='--remote-close' in sys.argv
ROOT=REMOTE if remote else LOCAL
B=ROOT/'evidence/recovery/2026-10-27/nimh-functional-03'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
    return h.hexdigest()
manifest=json.loads((B/'evidence-manifest.json').read_text())
if not remote:
    for name,r in manifest['files'].items():assert sha(B/name)==r['sha256'],name
    names=set()
    with tarfile.open(B/'functional-exports.tar.gz','r|gz') as tar:
        for member in tar:
            assert member.isfile(),member.name
            h=hashlib.sha256();f=tar.extractfile(member)
            for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
            assert h.hexdigest()==manifest['files'][member.name]['sha256'],member.name
            names.add(member.name)
    assert names==set(manifest['files'])-{'functional-exports.tar.gz'}
    proof=dict(passed=True,checked_files=len(manifest['files']),archive_members_checked=len(names),
        evidence_manifest_sha256=sha(B/'evidence-manifest.json'),archive_sha256=sha(B/'functional-exports.tar.gz'))
    (B/'mirror-audit.json').write_text(json.dumps(proof,indent=2)+'\n')
else:
    proof=json.loads((B/'mirror-audit.json').read_text())
    assert proof['passed']
    assert proof['evidence_manifest_sha256']==sha(B/'evidence-manifest.json')
    assert proof['archive_sha256']==sha(B/'functional-exports.tar.gz')
lib=ROOT/('uc-library' if remote else 'uc-library')
v=lib/'validation/nimh-functional-03';v.mkdir(parents=True,exist_ok=True)
coverage=json.loads((B/'functional-coverage.json').read_text())
audit=json.loads((B/'functional-audit.json').read_text())
summary=dict(phase='nimh-functional-03',pins=json.loads((B/'pins.json').read_text()),coverage=coverage,audit=audit,
    mirror=proof,cpp_readiness=False,hardware_validation=False,report='evidence/recovery/2026-10-27/nimh-functional-03/REPORT.md')
(v/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
heading='## NIMH FPGA partial functional logic and MCU interfaces — 2026-10-27'
fragment=f'''\n\n{heading}

Original mixer-13731 objects: `_ZL14nimh_fpga_code` and `_ZL13nimh_arm_code`;
input ELF SHA-256 `9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07`.

| Layer | Status and bounded coverage |
|---|---|
| FPGA functional source | Partial Verilog and {coverage['cone_equations']:,} equations; unsupported primitives explicit |
| Linux parsing | Full Verilog frontend and hierarchy check passed; full synthesis not admitted |
| Rewrite replay | {audit['compared_output_and_internal_values']:,} value and {audit['compared_register_transition_inputs']:,} transition-input comparisons, 64 abstract patterns, no skipped cases |
| Firmware interfaces | Static AVB banks, Ethernet/PTP, router, clock/HPLL and InS interfaces identified; exact fabric-cell and board-net attribution pending |
| C++ reconstruction / hardware | No embedded function readiness promotion; no hardware validation |

[Full evidence and remaining gaps]({B/'REPORT.md'}). Tool/database revisions,
source hashes, failed/limited attempts and mirror proof remain in this phase's evidence.
'''
(v/'tracker-fragment.md').write_text(fragment)
tracker=lib/'SYMBOLS.md';text=tracker.read_text()
if heading not in text:
    (v/'SYMBOLS-before.md').write_text(text)
    tracker.write_text(text+fragment)
else:assert fragment in text
print('Mirror/identity audit passed; sealed files:',proof['checked_files'],'archive members:',proof['archive_members_checked'])
print('Tracker updated:',tracker)
