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
MANGLED = "_ZN8Presonus7Surface23AssignEditPageComponent12paramChangedEPN4Core8Portable9ParameterEi"
ADDRESS, SIZE, OFFSET = 0x96E60, 152, 0x8EE60
BODY_SHA = "8c011014ce3f1cfc673f6480b9cdf991850882eb272937ca7c4c8108e9198bc4"


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
    sibling = Path(__file__).resolve().parent.parent
    visibility = json.loads((sibling/"cycle21_g04_s05/fixtures.json").read_text())["elf_observations"]
    aliases = json.loads((sibling/"cycle21_g04_s06/fixtures.json").read_text())["elf_observations"]
    base = [-1,80,80,80]
    out = []
    for visible,msg,name in ((1,3,"sel_chnum"),(1,3,"slot_bus_mode_02"),(1,3,"xslot_bus_mode"),
                             (1,3,"plain"),(1,2,"slot_bus_mode_02"),(0,3,"slot_bus_mode_02"),
                             (0,3,"sel_chnum"),(1,2,"sel_chnum")):
        uc=Uc(UC_ARCH_ARM,UC_MODE_ARM)
        uc.mem_map(0x8000,0x400000)
        for segment in elf.iter_segments():
            if segment["p_type"]=="PT_LOAD":
                uc.mem_write(segment["p_vaddr"],segment.data())
        assert bytes(uc.mem_read(ADDRESS,SIZE))==body
        uc.mem_map(0x800000,0x10000)
        obj,param,info,stop=0x801000,0x802000,0x803000,0x80F000
        uc.mem_write(param+12,struct.pack("<I",info))
        uc.mem_write(info+8,name.encode()+b"\0")
        result=base.copy()
        events=[]
        def text(a):
            return bytes(uc.mem_read(a,40)).split(b"\0",1)[0].decode()
        def hook(machine,pc,size,_):
            if pc not in (0x681D4,0x0B0F8,0xAE7C,0x95CD0,0x96A68):
                return
            a,b=[machine.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1)]
            returned=0
            if pc==0x681D4:
                assert a==obj
                returned=visible
                events.append(["visible",visible])
            elif pc==0x0B0F8:
                assert (text(a),text(b))==(name,"sel_chnum")
                returned=int(text(a)!=text(b))
                events.append(["strcmp",text(a),text(b)])
            elif pc==0xAE7C:
                assert (text(a),text(b))==(name,"slot_bus_mode")
                index=text(a).find(text(b))
                returned=0 if index<0 else a+index
                events.append(["strstr",index])
            else:
                assert a==obj
                src=visibility if pc==0x95CD0 else aliases
                command="visibility" if pc==0x95CD0 else "aliases"
                match=next(row for row in src if row["args"][1:6]==[1,1,1,1,1])
                events.append([command])
                if command=="visibility":
                    result[0]=match["expected"][0]
                else:
                    result[1:]=match["expected"][1:]
            machine.reg_write(UC_ARM_REG_R0,returned)
            machine.reg_write(UC_ARM_REG_PC,machine.reg_read(UC_ARM_REG_LR))
        uc.hook_add(UC_HOOK_CODE,hook)
        for reg,val in ((UC_ARM_REG_R0,obj),(UC_ARM_REG_R1,param),(UC_ARM_REG_R2,msg),
                        (UC_ARM_REG_SP,0x80E000),(UC_ARM_REG_LR,stop)):
            uc.reg_write(reg,val)
        uc.emu_start(ADDRESS,stop,count=250)
        assert uc.reg_read(UC_ARM_REG_PC)==stop
        out.append({"args":["changed",visible,1,1,1,1,msg,name],"expected":result,"events":events})
    return out


if __name__=="__main__":
    print(json.dumps({"elf_observations":observe_elf()},indent=2))
