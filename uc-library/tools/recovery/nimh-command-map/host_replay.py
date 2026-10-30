"""Execute selected original host ARM routines against explicit boundary models."""
from pathlib import Path
import hashlib
import json
import struct
import sys
import capstone as cs
import unicorn as uc
from unicorn import arm_const as arm
from elftools.elf.elffile import ELFFile

root = Path(sys.argv[1]).resolve()
out = root/'evidence/recovery/2026-10-27/nimh-command-map'
path = root/'evidence/recovery/2026-10-27/xmen-stm32/inputs/mixer-13731.elf'
raw = path.read_bytes()
assert hashlib.sha256(raw).hexdigest() == '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
stream = path.open('rb')
elf = ELFFile(stream)
symtab = elf.get_section_by_name('.symtab')
symbols = {s.name:s for s in symtab.iter_symbols() if s['st_value']}
names = {
    'clock':'_ZN8Presonus4NOAA5TCard14setClockSourceEi',
    'rate':'_ZN8Presonus4NOAA5TCard14sendSampleRateEii',
    'label':'_ZNK8Presonus4NOAA11SysexPacket18getSysexCommandStrEh',
    'arm_bundle':'_ZN8Presonus4NOAA5TCard20getArmFirmwareBundleEv',
    'fpga_bundle':'_ZN8Presonus4NOAA5TCard21getFpgaFirmwareBundleEv',
    'route':'_ZN8Presonus4NOAA11TCardRouter15doRouteCommandsEPNS0_9DiceRouteEih',
}
selected = []
dis = cs.Cs(cs.CS_ARCH_ARM, cs.CS_MODE_ARM)
with (out/'host-selected.arm.txt').open('w') as f:
    for key,n in names.items():
        if n not in symbols:
            continue
        s = symbols[n]
        sec = elf.get_section(s['st_shndx'])
        off = sec['sh_offset']+s['st_value']-sec['sh_addr']
        b = raw[off:off+s['st_size']]
        selected.append(dict(role=key,mangled=n,address=hex(s['st_value']),size=s['st_size'],
                             section=sec.name,file_offset=hex(off),sha256=hashlib.sha256(b).hexdigest()))
        f.write('\n# '+n+'\n')
        for i in dis.disasm(b,s['st_value']):
            f.write(f'{i.address:08x} {i.mnemonic} {i.op_str}\n')

def new_machine():
    m = uc.Uc(uc.UC_ARCH_ARM, uc.UC_MODE_ARM)
    pages=set()
    for seg in elf.iter_segments():
        if seg['p_type']=='PT_LOAD':
            pages.update(range(seg['p_vaddr']&~4095,(seg['p_vaddr']+seg['p_memsz']+4095)&~4095,4096))
    for a in sorted(pages):
        m.mem_map(a,4096)
    for seg in elf.iter_segments():
        if seg['p_type']=='PT_LOAD':
            m.mem_write(seg['p_vaddr'],seg.data())
    for a,size in ((0x70000000,0x10000),(0x71000000,0x10000),(0x72000000,4096)):
        m.mem_map(a,size)
    return m

def cstr(m,p):
    b=bytes(m.mem_read(p,512)).split(b'\0')[0]
    return b.decode('ascii','replace')

plt = elf.get_section_by_name('.plt')
rel = elf.get_section_by_name('.rel.plt')
dyn = elf.get_section(rel['sh_link'])
plt_names={plt['sh_addr']+20+i*12:dyn.get_symbol(r['r_info_sym']).name for i,r in enumerate(rel.iter_relocations())}
core_hooks={s['st_value']:n for n,s in symbols.items() if
            n.startswith('_ZN4Core11DebugPrintf') or n.startswith('_ZN4Core15GetAbsoluteTime') or
            n in ('__aeabi_ldivmod',) or n=='_ZN8Presonus4NOAA13SysexReceiver7waitAckEx'}
stop,post,obj,vtable = 0x72000000,0x72000004,0x71000000,0x71001000

def run(kind,value,link=0,model=0):
    m = new_machine()
    m.mem_write(obj, struct.pack('<I',vtable)+bytes(0x100))
    m.mem_write(obj+0x3c,struct.pack('<I',model))
    m.mem_write(vtable,struct.pack('<III',0,0,post))
    m.reg_write(arm.UC_ARM_REG_SP,0x7000f000)
    m.reg_write(arm.UC_ARM_REG_LR,stop)
    for r,v in ((arm.UC_ARM_REG_R0,obj),(arm.UC_ARM_REG_R1,value),(arm.UC_ARM_REG_R2,link)):
        m.reg_write(r,v)
    frames,models,trace = [],[],[]
    def ret(v=0):
        m.reg_write(arm.UC_ARM_REG_R0,v)
        m.reg_write(arm.UC_ARM_REG_R1,0)
        m.reg_write(arm.UC_ARM_REG_PC,m.reg_read(arm.UC_ARM_REG_LR))
    def hook(m,a,size,_):
        trace.append(a)
        if a==stop:
            m.emu_stop(); return
        if a==post:
            p=m.reg_read(arm.UC_ARM_REG_R1)
            length=m.mem_read(p+0x108,1)[0]
            assert 0<length<=255
            frames.append(bytes(m.mem_read(p+8,length)).hex())
            models.append('virtual transport post captured; no SPI device')
            ret();return
        name=plt_names.get(a) or core_hooks.get(a)
        if not name:
            return
        r0,r1,r2=[m.reg_read(x) for x in (arm.UC_ARM_REG_R0,arm.UC_ARM_REG_R1,arm.UC_ARM_REG_R2)]
        models.append(name)
        if name in ('memcpy','memmove'):
            assert r2<=4096
            m.mem_write(r0,bytes(m.mem_read(r1,r2)));ret(r0)
        elif name=='memset':
            assert r2<=4096
            m.mem_write(r0,bytes([r1&255])*r2);ret(r0)
        elif ('DebugPrintf' in name or 'GetAbsoluteTime' in name or
              name=='__aeabi_ldivmod' or 'waitAck' in name):
            ret()
        else:
            raise AssertionError('unmodelled external boundary '+name)
    m.hook_add(uc.UC_HOOK_CODE,hook)
    m.emu_start(symbols[names[kind]]['st_value'],0,count=30000)
    assert trace[-1]==stop,hex(trace[-1])
    return dict(method=kind,argument=value,link_id=link,model=model,
                packets=frames,boundary_models=sorted(set(models)),instructions=len(trace))

cases=[]
for v in (0,1,2,15,16,127,255):
    c=run('clock',v)
    assert c['packets']==[bytes((0xf0,0x28,(v>>4)&15,v&15,0xf7)).hex()],c
    cases.append(c)
for rate in (0,1,2,3):
    for link in (0,1,127):
        c=run('rate',rate,link)
        assert c['packets']==[bytes((0xf0,0x11,rate,link&127,0xf7)).hex()]
        cases.append(c)
for rate in (0,1,2,3):
    for model in (23,24):
        c=run('rate',rate,3,model)
        assert c['packets']==[bytes((0xf0,0x21,int(rate>1),0xf7)).hex(),bytes((0xf0,0x11,rate,3,0xf7)).hex()]
        cases.append(c)
labels={}
for cmd in [1,2,3,4,5,9,*range(17,31),64]:
    m=new_machine()
    m.reg_write(arm.UC_ARM_REG_SP,0x7000f000)
    m.reg_write(arm.UC_ARM_REG_LR,stop)
    m.reg_write(arm.UC_ARM_REG_R1,cmd)
    m.hook_add(uc.UC_HOOK_CODE,lambda m,a,s,u:m.emu_stop() if a==stop else None)
    m.emu_start(symbols[names['label']]['st_value'],0,count=1000)
    assert m.reg_read(arm.UC_ARM_REG_PC)==stop
    labels[hex(cmd)]=cstr(m,m.reg_read(arm.UC_ARM_REG_R0))
(out/'host-replay.json').write_text(json.dumps(dict(
    original_elf_sha256=hashlib.sha256(raw).hexdigest(),functions=selected,
    cases=cases,command_labels=labels,
    scope='actual selected host ARM packet assembly; libc/time/log/ack and virtual post modelled; not SPI, timing, ACK semantics, or hardware proof',
    tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2)+'\n')
print('Host packet cases passed:',len(cases),'command labels:',labels)
