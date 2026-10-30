"""Independent ELF32 section/symbol/range hash audit; no code execution."""
import hashlib
import json
from pathlib import Path
import struct

root=Path('/home/rs/projects/opencs/ai-line-analysis')
host=root/'evidence/recovery/2026-10-27/efm-reconstruction/host'
target='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
choices=[root/'Cutter Analysis/surface',root/'rootfs/CS18_v13840/home/root/surface']
inputs=root/'evidence/recovery/2026-10-27/efm32-faders/inputs'
if inputs.exists():choices.extend(p for p in inputs.iterdir() if p.is_file())
source=None
for p in choices:
    if p.is_file() and sha(p.read_bytes())==target:
        source=p;break
assert source is not None,'Selected source ELF unavailable'
raw=source.read_bytes()
assert raw[:7]==b'\x7fELF\x01\x01\x01' and struct.unpack_from('<H',raw,18)[0]==40
shoff=struct.unpack_from('<I',raw,32)[0]
entsize,count=struct.unpack_from('<HH',raw,46)
assert entsize==40 and count>0
sections=[struct.unpack_from('<IIIIIIIIII',raw,shoff+i*entsize) for i in range(count)]
symbols={}
for section in sections:
    if section[1] not in (2,11):continue
    assert section[9]==16
    strings_section=sections[section[6]]
    strings=raw[strings_section[4]:strings_section[4]+strings_section[5]]
    for offset in range(section[4],section[4]+section[5],16):
        name,value,size,info,other,index=struct.unpack_from('<IIIBBH',raw,offset)
        end=strings.find(b'\0',name);assert end>=name
        label=strings[name:end].decode('utf-8')
        symbols.setdefault(label,[]).append((value,size,index,info&15))
range_path=host/'ranges.json';table=json.loads(range_path.read_text())
assert table['source_elf_sha256']==target
checks=[]
for row in table['symbols']:
    kind={'STT_FUNC':2,'STT_OBJECT':1}[row['kind']]
    assert (row['address'],row['size'],row['section'],kind) in symbols[row['mangled']]
    section=sections[row['section']];assert section[1]!=8
    relative=row['address']-section[3]
    assert relative>=0 and relative+row['size']<=section[5]
    offset=section[4]+relative;assert offset==row['file_offset']
    data=raw[offset:offset+row['size']]
    export=host/'ranges'/(row['mangled']+'.bin')
    assert len(data)==row['size'] and sha(data)==row['sha256']==sha(export.read_bytes())
    checks.append(dict(mangled=row['mangled'],kind=row['kind'],address=row['address'],file_offset=offset,size=len(data),sha256=sha(data)))
manifest_checks=0
for line in (host/'SHA256SUMS').read_text().splitlines():
    digest,name=line.split('  ',1)
    path=(host/name).resolve();assert path.is_relative_to(host.resolve())
    assert sha(path.read_bytes())==digest,name
    manifest_checks+=1
result=dict(passed=True,scope='Independent source ELF identity/symbol/section/range and receipt-file hashes only; no semantic, ABI or hardware validation',source_elf=str(source.relative_to(root)),source_elf_sha256=target,range_receipt_sha256=sha(range_path.read_bytes()),ranges=checks,range_count=len(checks),manifest_file_hashes=manifest_checks,firmware_executed=False,hardware_accessed=False)
output=root/'evidence/recovery/2026-10-27/efm-reconstruction/cross-layer/host-byte-audit.json'
output.parent.mkdir(parents=True,exist_ok=True)
output.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(passed=True,ranges=len(checks),receipt_files=manifest_checks,source_elf_sha256=target)))
