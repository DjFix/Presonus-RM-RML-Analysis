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
MANGLED = "_ZN8Presonus7Surface23AssignEditPageComponent18updateAliasTargetsEv"
ADDRESS, SIZE, OFFSET = 0x96A68, 964, 0x8EA68
BODY_SHA = "35ded9d0d3a1fdba27ef6c994285f85dc385391ab02b3cf6aecf8bb1042b8566"


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
    result = []
    scenarios = ((0,1,1),(1,0,1),(1,2,1),(1,5,1),(1,6,1),
                 (1,1,1),(1,1,2),(1,3,3),(1,1,3),(1,1,4),(1,1,0),(1,4,1))
    for visible, mixer, selected in scenarios:
        uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        uc.mem_map(0x8000,0x400000)
        for segment in elf.iter_segments():
            if segment["p_type"] == "PT_LOAD":
                uc.mem_write(segment["p_vaddr"],segment.data())
        assert bytes(uc.mem_read(ADDRESS,SIZE))==body
        uc.mem_map(0x800000,0x20000)
        obj,mx,slave=(0x801000,0x802000,0x803000)
        inputs,returns,buses,remote=(0x804000,0x805000,0x806000,0x807000)
        i,r,s,b1,b2,other=(0x808000,0x809000,0x80A000,0x80B000,0x80C000,0x80D000)
        ali,chan,mode,wrong=(0x80E000,0x80E100,0x80E200,0x80E300)
        vtable,h,stop=(0x80F000,0x810000,0x81E000)
        selected_addr=(0,i,r,s,other)[selected]
        aliases={ali:80,chan:80,mode:80}
        assignment_ids={i:251,r:252,s:253}
        names={"slot_assign_02":ali,"slot_chname_02":chan,"slot_bus_mode_02":mode,
               "slot_assign_01":wrong}
        events=[]
        def write(addr,v):
            uc.mem_write(addr,struct.pack("<I",v))
        def text(addr):
            return bytes(uc.mem_read(addr,32)).split(b"\0",1)[0].decode()
        def put(addr,chars):
            uc.mem_write(addr,chars.encode()+b"\0")
        write(obj+0xCC,mx if mixer else 0)
        for item in (obj,mx,slave): write(item,vtable)
        for offset, target in ((0x18,h),(0x1C,h+4),(0x20,h+8),(0x28,h+12)):
            write(vtable+offset,target)
        for index,(group,children) in enumerate(((inputs,[i]),(returns,[r]),(buses,[b1,b2]),(remote,[s]))):
            addr=0x811000+16*index
            write(group+0x58,addr); write(group+0x5C,len(children))
            for child_index, child in enumerate(children): write(addr+4*child_index,child)
        def hook(machine, pc, length, _):
            if pc not in (0x681D4,0x24268,0x4B47C,0xAE58,0x11ACF0,0x120E24,h,h+4,h+8,h+12):
                return
            a,b,c,d=[machine.reg_read(reg) for reg in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
            returned=0
            if pc==0x681D4:
                assert a==obj
                returned=visible
                events.append(["visible",visible])
            elif pc==h+8:
                assert (a==mx and b in (0,2,4)) or (a==slave and b==0)
                returned=remote if a==slave else {0:0 if mixer==5 else inputs,2:0 if mixer==6 else returns,4:0 if mixer==2 else buses}[b]
                events.append(["group","slave" if a==slave else "main",b,bool(returned)])
            elif pc==h+12:
                assert a==mx
                returned=slave if mixer==3 else 0
                events.append(["slave",bool(returned)])
            elif pc==h+4:
                assert a==mx
                returned=selected_addr
                events.append(["selected",selected])
            elif pc==0x24268:
                prefix=text(b)
                assert prefix in ("slot_assign","slot_bus_mode","slot_chname")
                put(a,prefix)
            elif pc==0x4B47C:
                assert text(b)=="_%02d" and 1<=c<=16
                put(a,text(a)+(text(b) % c))
            elif pc==h:
                assert a==obj
                name=text(b)
                returned=names.get(name,0)
                events.append(["find",name,bool(returned)])
            elif pc==0xAE58:
                assert a in names.values() and (b,c,d)==(2118576,2118344,0)
                returned=0 if a==wrong else a
                events.append(["cast",a,bool(returned)])
            elif pc==0x11ACF0:
                if a==b2 and b==2:
                    returned=2
                elif a==b2 and b==411 and mixer!=4:
                    returned=411
                elif a in assignment_ids and b==257:
                    returned=assignment_ids[a]
                events.append(["tag",a,b,returned])
            else:
                assert a in aliases and (b in (0,2,411) or b in tuple(assignment_ids.values()))
                aliases[a]=b
                events.append(["connect",a,b])
            machine.reg_write(UC_ARM_REG_R0,returned)
            machine.reg_write(UC_ARM_REG_PC,machine.reg_read(UC_ARM_REG_LR))
        uc.hook_add(UC_HOOK_CODE,hook)
        for reg,val in ((UC_ARM_REG_R0,obj),(UC_ARM_REG_SP,0x81D000),(UC_ARM_REG_LR,stop)):
            uc.reg_write(reg,val)
        uc.emu_start(ADDRESS,stop,count=10000)
        assert uc.reg_read(UC_ARM_REG_PC)==stop
        result.append({"args":["aliases",visible,mixer,selected,1,1,0,"plain"],
                       "expected":[-1,aliases[ali],aliases[chan],aliases[mode]],"events":events})
    return result


if __name__=="__main__":
    print(json.dumps({"elf_observations":observe_elf()},indent=2))
