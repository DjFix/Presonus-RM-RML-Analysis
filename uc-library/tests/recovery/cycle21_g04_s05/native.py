"""Replay a verified original ARM application routine at isolated provider boundaries."""
import hashlib
import struct
import json
from pathlib import Path
from io import BytesIO

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP

BASE = Path("/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261121/packeting")
MAP = BASE / "READ_INPUTS-post32-next-batch02-cycle21_g04-post32-next39-scoped03-dispatch02.json"
ORIGINAL = "rootfs/CS18_v13840/home/root/surface"
ELF_SHA = "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0"
MANGLED = "_ZN8Presonus7Surface23AssignEditPageComponent16updateVisibilityEv"
ADDRESS, SIZE, OFFSET = 0x95CD0, 232, 0x8DCD0
BODY_SHA = "c7c66b317bea029252f7df3724955ac90c7a57f70584fb14b697e59509b15c1c"


def observe_elf():
    path = Path(json.loads(MAP.read_text())[ORIGINAL]["frozen_read_path"])
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ELF_SHA
    elf = ELFFile(BytesIO(raw))
    symbol = elf.get_section_by_name(".symtab").get_symbol_by_name(MANGLED)[0]
    section = elf.get_section(symbol["st_shndx"])
    assert section.name == ".text"
    assert (symbol["st_value"], symbol["st_size"]) == (ADDRESS, SIZE)
    assert section["sh_offset"] + ADDRESS - section["sh_addr"] == OFFSET
    body = raw[OFFSET:OFFSET + SIZE]
    assert hashlib.sha256(body).hexdigest() == BODY_SHA
    rows = []
    for visible, mixer, value in ((0,1,1),(1,0,1),(1,2,1),(1,1,-1),(1,1,0),(1,1,1),(1,4,1)):
        uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        uc.mem_map(0x8000, 0x400000)
        for segment in elf.iter_segments():
            if segment["p_type"] == "PT_LOAD":
                uc.mem_write(segment["p_vaddr"], segment.data())
        assert bytes(uc.mem_read(ADDRESS,SIZE)) == body
        uc.mem_map(0x800000,0x10000)
        obj, mx, buses, empty, bus = (0x801000,0x802000,0x803000,0x804000,0x805000)
        data, vis, mode, virtuals, stop = (0x806000,0x807000,0x807100,0x808000,0x80F000)
        slots = {0x681D4:"visible",0x11ACF0:"tag",0x808800:"group",0x808804:"get",0x808808:"set"}
        events=[]
        result = -1
        def w(a,v):
            uc.mem_write(a,struct.pack("<I",v))
        w(obj+0xCC,mx if mixer else 0)
        w(mx,virtuals); w(virtuals+0x20,0x808800)
        w(buses+0x58,data); w(buses+0x5C,2)
        w(data,empty); w(data+4,bus)
        w(mode,virtuals); w(vis,virtuals)
        w(virtuals+0x44,0x808804); w(virtuals+0x58,0x808808)
        def hook(machine, pc, size, _):
            nonlocal result
            if pc==0x1877E0:
                events.append(["fcmpgt"])
            if pc not in slots:
                return
            a,b,c=[machine.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2)]
            name=slots[pc]
            if name=="visible":
                assert a==obj
                returned=visible
                events.append([name,returned])
            elif name=="group":
                assert a==mx and b==4
                returned=buses if mixer!=2 else 0
                events.append([name,b,bool(returned)])
            elif name=="tag":
                returned=vis if a==obj else mode if a==bus and mixer!=4 else 0
                assert b==(1000 if a==obj else 411)
                events.append([name,b,bool(returned)])
            elif name=="get":
                assert a==mode
                returned=struct.unpack("<I",struct.pack("<f",value))[0]
                events.append([name,value])
            else:
                assert a==vis and c==0
                result=int(struct.unpack("<f",struct.pack("<I",b))[0])
                returned=0
                events.append([name,result,c])
            machine.reg_write(UC_ARM_REG_R0,returned)
            machine.reg_write(UC_ARM_REG_PC,machine.reg_read(UC_ARM_REG_LR))
        uc.hook_add(UC_HOOK_CODE,hook)
        for reg,val in ((UC_ARM_REG_R0,obj),(UC_ARM_REG_SP,0x80E000),(UC_ARM_REG_LR,stop)):
            uc.reg_write(reg,val)
        uc.emu_start(ADDRESS,stop,count=260)
        assert uc.reg_read(UC_ARM_REG_PC)==stop
        rows.append({"args":["visibility",visible,mixer,1,value,1,0,"plain"],
                     "expected":[result,80,80,80],"events":events})
    return rows


if __name__=="__main__":
    print(json.dumps({"elf_observations":observe_elf()},indent=2))
