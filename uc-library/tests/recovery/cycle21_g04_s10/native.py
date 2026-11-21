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
ORIGINAL = "rootfs/RML16AI_Rack_13731/home/root/mixer"
ELF_SHA = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
MANGLED = "_ZN8Presonus5Mixer12AliasMapping7connectEPNS_24MixerClientComponentBaseE"
ADDRESS, SIZE, OFFSET = 0x1D068, 156, 0x15068
BODY_SHA = "6b33e260ff333b9f4d51d248aab4e6ecb0fa325cda5cab34e1cb3c5bd7d02da9"


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
    result=[]
    for mode in (0,1,2):
        for enabled,prior in ((0,0),(0,1),(1,1)):
            uc=Uc(UC_ARCH_ARM,UC_MODE_ARM)
            uc.mem_map(0x8000,0x700000)
            for segment in elf.iter_segments():
                if segment["p_type"]=="PT_LOAD":
                    uc.mem_write(segment["p_vaddr"],segment.data())
            assert bytes(uc.mem_read(ADDRESS,SIZE))==body
            uc.mem_map(0x800000,0x10000)
            obj,mx,alias,virtuals,h,stop=(0x801000,0x802000,0x803000,0x804000,0x805000,0x80F000)
            def write(a,v):
                uc.mem_write(a,struct.pack("<I",v))
            path="missing/gain" if mode==2 else "channel/gain"
            uc.mem_write(obj+4,path.encode()+b"\0")
            write(obj+0x24,5);write(obj+0x28,alias)
            write(alias,virtuals);write(virtuals+0x20,h);write(virtuals+0x24,h+4)
            event=[]
            target=6 if prior else 0
            state={4:True,5:True,6:bool(enabled),0:False}
            def hook(machine,pc,size,_):
                nonlocal target
                if pc not in (0x11B968,0x11EE28,h,h+4):
                    return
                a,b=[machine.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1)]
                ret=0
                if pc==0x11B968:
                    assert a==mx+0x30 and b==obj+4
                    assert bytes(machine.mem_read(b,len(path)+1))==path.encode()+b"\0"
                    ret=4 if mode==1 else 0
                    event.append(["lookup",path,ret])
                elif pc==h:
                    assert a==alias
                    ret=int(state[target])
                    event.append(["isEnabled",target,ret])
                elif pc==0x11EE28:
                    assert a==alias and b in (4,5)
                    target=b
                    event.append(["setOriginal",target])
                else:
                    assert a==alias and b in (0,1)
                    state[target]=bool(b)
                    event.append(["enable",target,b])
                machine.reg_write(UC_ARM_REG_R0,ret)
                machine.reg_write(UC_ARM_REG_PC,machine.reg_read(UC_ARM_REG_LR))
            uc.hook_add(UC_HOOK_CODE,hook)
            for reg,value in ((UC_ARM_REG_R0,obj),(UC_ARM_REG_R1,mx if mode else 0),
                              (UC_ARM_REG_SP,0x80E000),(UC_ARM_REG_LR,stop)):
                uc.reg_write(reg,value)
            uc.emu_start(ADDRESS,stop,count=230)
            assert uc.reg_read(UC_ARM_REG_PC)==stop
            result.append({"args":[mode,enabled,prior],
                           "expected":[target,int(state[target]),int(state[4]),int(state[5])],
                           "events":event})
    return result


if __name__=="__main__":
    print(json.dumps({"elf_observations":observe_elf()},indent=2))
