"""Validate current analysis artifacts and publish an extraction-only tracker entry."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,shutil,sys,tarfile
root=Path(sys.argv[1]).resolve()
out=root/'evidence/recovery/2026-10-27/nimh-command-map'
ops=root/'uc-library/tools/recovery/nimh-command-map'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(n):return json.loads((out/n).read_text())
analysis,host,stm,fpga=[read(n) for n in ('analysis.json','host-replay.json','stm-replay.json','fpga-register-replay.json')]
for proof,script in ((analysis,'analyze.py'),(host,'host_replay.py'),(stm,'stm_replay.py'),(fpga,'fpga_replay.py')):
    assert proof['tool_sha256']==sha(ops/script),script
assert len(host['cases'])==27 and len(stm['cases'])==222 and len(stm['worker_cases'])==12 and len(fpga['cases'])==216
assert analysis['startup_replay_passed'] and not fpga['other_firmware_compared']
image=root/'evidence/recovery/2026-10-27/xmen-stm32/images/mixer-analysis/_ZL13nimh_arm_code.bin'
assert sha(image)==analysis['image_sha256']==stm['image_sha256']==fpga['image_sha256']
for d in read('docs/sources.json'):
    assert sha(root/d['path'])==d['sha256'],d['path']
ecos=read('ecos-source.json')
archive=out/ecos['archive']
assert sha(archive)==ecos['archive_sha256']
expected={r['path']:r for r in ecos['files']}
with tarfile.open(archive) as t:
    actual={}
    for m in t.getmembers():
        assert not m.name.startswith('/') and '..' not in Path(m.name).parts
        if m.isfile():
            actual[m.name]=hashlib.sha256(t.extractfile(m).read()).hexdigest()
        else:assert m.isdir()
    assert set(actual)==set(expected)
    assert all(actual[n]==expected[n]['sha256'] for n in actual)
    t.extractall(ops/'ecos-source',filter='data')
assert sha(ops/'ecos-source/ecos-reference/packages/hal/cortexm/arch/current/src/hal_misc.c')==ecos['reset_reference']['sha256']
elf=root/'evidence/recovery/2026-10-27/xmen-stm32/inputs/mixer-13731.elf'
assert sha(elf)==host['original_elf_sha256']==analysis['host_elf_sha256']
data=elf.read_bytes()
inventory=json.loads((root/'uc-library/recovered-all/server/all-symbols.json').read_text())
by={s['mangled']:s for s in inventory}
identities=[]
for s in host['functions']:
    off=int(s['file_offset'],16)
    assert hashlib.sha256(data[off:off+s['size']]).hexdigest()==s['sha256']
    r=dict(s,demangled=by[s['mangled']]['demangled'],firmware_version='mixer 13731',
           input_elf_sha256=sha(elf))
    identities.append(r)
(out/'host-symbol-index.json').write_text(json.dumps(identities,indent=2)+'\n')
tools=out/'tools';tools.mkdir(exist_ok=True)
for p in ops.glob('*.py'):shutil.copyfile(p,tools/p.name)
linked=root/'uc-library/validation/fpga-identification/assessment.json'
assert json.loads(linked.read_text())['firmware_scope']['mixer']['elf_sha256']==sha(elf)
summary=dict(phase='nimh-command-map-01',sealed_at=datetime.now(timezone.utc).isoformat(),
             host_elf_sha256=sha(elf),nimh_image_sha256=sha(image),
             startup_replay_passed=True,host_packet_cases=27,stm_command_cases=222,
             deferred_consumer_cases=12,nimh_register_cases=216,
             cli_descriptor_records=analysis['cli_records'],sdk_path_strings=analysis['sdk_source_paths'],
             ecos_reference_commit=ecos['commit'],ecos_exact_vendor_revision=None,
             docs_manifest_sha256=sha(out/'docs/sources.json'),
             linked_fpga_thread='01a17e03-d528-7102-af84-2a680a143ee3',
             linked_fpga_assessment_sha256=sha(linked),
             cs18_firmware_comparison=False,production_cpp_changed=False,
             recovered_function_promotions=0,hardware_actions=0,
             limitations=['RX queue/physical SPI/DMA framing not executed; frames injected.',
                          'SDK hardware operations, scheduler and completion boundaries modelled.',
                          'Worker replay only inactive-state handoff; full topology/clock lock unresolved.',
                          'MMIO writes validated against RAM; FPGA interpretation/audio/timing unresolved.',
                          'Public eCos snapshot is a source reference, not proven TCAT original source.'])
validation=root/'uc-library/validation/nimh-command-map'
validation.mkdir(parents=True,exist_ok=True)
index='# NIMH offline startup and command-map checkpoint\n\nFull phase evidence is in project `evidence/recovery/2026-10-27/nimh-command-map/`, including `REPORT.md`, original-code replays, local manual hashes and pinned eCos sources.\n\nNo production C++ or readiness ledger changes. Current proof: [validation.json](validation.json).\n'
(validation/'README.md').write_text(index)
fragment='''
## NIMH STM32 startup and command paths — phase 01

Original embedded object `_ZL13nimh_arm_code`, mixer 13731 ELF SHA-256
`9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07`,
image SHA-256 `b0979352e18a1093051fc6118a47694773cb9240e88087eca03aaa2ffe0f5e17`.
[Phase proof](validation/nimh-command-map/validation.json) and
[evidence index](validation/nimh-command-map/README.md).

| Scope | Byte identity | Analysis | Offline native validation | C++ / hardware |
| --- | --- | --- | --- | --- |
| Startup / memory | verified | eCos reset pattern, data/BSS/vector ranges | Bounded startup replay; hardware init/SVC hooked | pending |
| Host clock/rate packets | original ELF identities and ranges verified | 0x11 rate/link and 0x28 AVB source paths | 27 cases; libc/time/log/ACK/transport models | no new production C++ |
| STM32 commands | verified image | Dispatcher and SDK boundaries | 222 cases; 12 deferred-consumer cases | full scheduler/device behavior pending |
| NIMH mixer callback | verified image | CLI mix.gain pointer and external register write | 216 index/gain/error cases against RAM MMIO | FPGA/audio/timing pending |
| SDK / RTOS | verified image and source references | 124 CLI records, 24 SDK path strings; public eCos source pinned | exact TCAT eCos revision unresolved | no source/body equivalence promotion |

Embedded function labels are analysis identities, not original C/C++ symbols.
This phase follows local manual architecture and uses no CS18AI/RM firmware
mapping/comparison. Zero function promotions and zero hardware actions.
'''
(out/'tracker-fragment.md').write_text(fragment)
tracker=root/'uc-library/SYMBOLS.md'
before=tracker.read_text()
heading='## NIMH STM32 startup and command paths — phase 01'
if heading not in before:
    (out/'SYMBOLS-before-linux.md').write_text(before)
    with tracker.open('a') as f:f.write(fragment)
else:assert fragment in before
summary['tracker_sha256']=sha(tracker)
summary['artifact_hashes']={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*'))
                            if p.is_file() and not p.is_symlink() and p.name not in ('validation.json','seal.log')
                            and '__pycache__' not in p.parts}
(out/'validation.json').write_text(json.dumps(summary,indent=2)+'\n')
shutil.copyfile(out/'validation.json',validation/'validation.json')
print(json.dumps({k:v for k,v in summary.items() if k not in ('artifact_hashes','limitations')},indent=2))
