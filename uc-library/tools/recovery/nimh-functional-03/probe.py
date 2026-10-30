"""Read-only inventories to scope functional reconstruction on VM101."""
import json, re, hashlib
from collections import Counter, defaultdict
from pathlib import Path
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_LITTLE_ENDIAN
from capstone.arm import ARM_OP_MEM, ARM_OP_IMM, ARM_REG_PC

ROOT=Path('/home/rs/projects/opencs/ai-line-analysis')
BASE=ROOT/'evidence/recovery/2026-10-27/nimh-fpga-connectivity-02'
OUT=ROOT/'evidence/recovery/2026-10-27/nimh-functional-03'
OUT.mkdir(parents=True,exist_ok=True)
def save(n,v): (OUT/n).write_text(json.dumps(v,indent=2)+'\n')
rows=lambda p: (json.loads(l) for l in p.open())
settings=defaultdict(dict)
for r in rows(BASE/'dependencies/primitive-settings.jsonl'):
    if 'bel' in r and 'value' in r: settings[r['tile'].split('.')[0]+'.'+r['bel']][r['attribute']]=r['value']
sources=Counter()
for r in rows(BASE/'input-pin-net-status.jsonl'):
    sources[r.get('abstract_source','unresolved')]+=1
used=defaultdict(list)
for name,c in sources.items():
    if name.startswith('primitive:'):
        p,pin=name[10:].rsplit('.',1);used[p].append(pin)
inv=[]
for r in rows(BASE/'export/primitives.jsonl'):
    p=r['id']; a=settings[p]
    if used[p] or (r['class']=='OLOGIC' and a.get('ENABLE')=='1'):
        inv.append(dict(primitive=p,cls=r['class'],outputs=used[p],settings=a))
save('primitive-inventory.json',inv)
fw=ROOT/'evidence/recovery/2026-10-27/xmen-stm32/images/mixer-analysis/_ZL13nimh_arm_code.bin'
data=fw.read_bytes();base=0x08000000
assert hashlib.sha256(data).hexdigest()=='b0979352e18a1093051fc6118a47694773cb9240e88087eca03aaa2ffe0f5e17'
strings=[]
for m in re.finditer(rb'[\x20-\x7e]{5,}',data):
    strings.append(dict(offset=hex(m.start()),address=hex(base+m.start()),text=m.group().decode()))
save('stm32-strings.json',strings)
md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_LITTLE_ENDIAN);md.detail=True;md.skipdata=True
insns=list(md.disasm(data,base))
lines=[];literal_refs=[]
for i in insns:
    lines.append(f'{i.address:08x}: {i.bytes.hex():8} {i.mnemonic:9} {i.op_str}')
    if i.id==0:continue
    if i.mnemonic.startswith('ldr') and len(i.operands)>1:
        op=i.operands[1]
        if op.type==ARM_OP_MEM and op.mem.base==ARM_REG_PC:
            addr=((i.address+4)&~3)+op.mem.disp;off=addr-base
            if 0<=off<=len(data)-4:
                value=int.from_bytes(data[off:off+4],'little')
                literal_refs.append(dict(instruction=hex(i.address),mnemonic=i.mnemonic,operand=i.op_str,literal=hex(addr),value=hex(value)))
(OUT/'stm32-linear-candidates.txt').write_text('\n'.join(lines)+'\n')
save('stm32-literal-candidates.json',literal_refs)
interesting=[s for s in strings if re.search(r'ptp|1722|avb|ether|rgmii|mii|spi|fpga|fsmc|nimh|hpll|router|InS|timestamp',s['text'],re.I)]
save('stm32-interesting-strings.json',interesting)
print('Referenced output primitive classes:',dict(Counter(r['cls'] for r in inv)))
print('Literal candidate address groups:',Counter(int(r['value'],16)>>24 for r in literal_refs if 0x40000000<=int(r['value'],16)<0xe0000000))
print('Selected firmware strings:',len(interesting))
for s in interesting: print(s['address'],s['text'])
