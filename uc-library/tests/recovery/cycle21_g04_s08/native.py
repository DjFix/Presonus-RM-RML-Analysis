"""Exercise the exact Scenes ARM callback with independently run CCL providers."""
import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import struct
import subprocess

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0,
    UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP,
)

ROOT = Path("/home/rs/projects/opencs/ai-line-analysis")
READ_MAP = ROOT / "temp/recovery-work/reconstruction10x10-20261121/packeting/READ_INPUTS-post32-next-batch02-cycle21_g04-post32-next39-scoped04-dispatch02.json"
ELF_NAME = "rootfs/CS18_v13840/home/root/surface"
ELF_SHA = "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0"
MANGLED = "_ZN8Presonus7Surface19ScenesPageComponent12paramChangedEPN4Core8Portable9ParameterEi"
ADDRESS, SIZE, OFFSET = 0xB4A98, 140, 0xACA98
BODY_SHA = "214016847c6c73b7e7b6b782edd8914aa32d5e7fca2795fc154373f0bd449fe2"
COMPARE, BASE, VISIBLE, FLOAT_GT = 0xB0F8, 0xB47B0, 0x681D4, 0x1877E0


def observe(executable):
    raw = Path(json.loads(READ_MAP.read_text())[ELF_NAME]["frozen_read_path"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ELF_SHA
    elf = ELFFile(BytesIO(raw))
    symbols = elf.get_section_by_name(".symtab")
    sym = symbols.get_symbol_by_name(MANGLED)[0]
    assert (sym["st_value"], sym["st_size"], sym["st_shndx"]) == (ADDRESS, SIZE, 12)
    section = elf.get_section(sym["st_shndx"])
    assert section.name == ".text"
    assert section["sh_offset"] + ADDRESS - section["sh_addr"] == OFFSET
    body = raw[OFFSET:OFFSET + SIZE]
    assert hashlib.sha256(body).hexdigest() == BODY_SHA

    def slot(table, offset, target):
        sym = symbols.get_symbol_by_name(table)[0]
        backing = elf.get_section(sym["st_shndx"])
        address = sym["st_value"] + 8 + offset
        word, = struct.unpack_from("<I", backing.data(), address - backing["sh_addr"])
        assert symbols.get_symbol_by_name(target)[0]["st_value"] == word
        return {"table": table, "slot": offset, "word_address": address,
                "value": word, "mangled": target}

    slot_evidence = [
        slot("_ZTVN4Core8Portable12NumericParamE", 0x44, "_ZNK4Core8Portable12NumericParam8getValueEv"),
        slot("_ZTVN8Presonus7Surface19ScenesPageComponentE", 0x54, "_ZN8Presonus7Surface20PresetsPageComponent6recallEv"),
    ]
    assert symbols.get_symbol_by_name("_ZN8Presonus7Surface20PresetsPageComponent12paramChangedEPN4Core8Portable9ParameterEi")[0]["st_value"] == BASE
    out = []
    for args in ((1,3,0,1,1),(1,3,0,0,1),(1,3,0,-1,1),(1,3,0,1,0),
                 (0,3,0,1,1),(1,2,0,1,1),(1,3,1,1,1),(1,2,2,1,1),
                 (0,2,2,0,1),(1,0,0,1,1)):
        shown, message, kind, value, _ = args
        label = ("fsw_load", "other", "selected")[kind]
        uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        uc.mem_map(0x8000, 0x400000)
        for segment in elf.iter_segments():
            if segment["p_type"] == "PT_LOAD":
                uc.mem_write(segment["p_vaddr"], segment.data())
        assert bytes(uc.mem_read(ADDRESS, SIZE)) == body
        uc.mem_map(0x800000, 0x10000)
        obj, param, info, vtable, get, recall, stop = (0x801000,0x802000,0x803000,
                                                       0x804000,0x805000,0x805004,0x80F000)
        def word(a,v):
            uc.mem_write(a,struct.pack("<I",v))
        def read(a):
            return bytes(uc.mem_read(a, 32)).split(b"\0",1)[0].decode()
        word(obj,vtable)
        word(param,vtable)
        word(vtable+0x44,get)
        word(vtable+0x54,recall)
        word(param+12,info)
        uc.mem_write(info+8,label.encode()+b"\0")
        result = []
        events = []

        def provider(mode):
            values = list(map(int,subprocess.check_output(
                [str(executable.resolve()),mode,*map(str,args)],text=True).split()))
            assert values[3:6] == [0,-99,-1]
            return values

        def hook(machine,pc,size,_):
            if pc == FLOAT_GT:
                events.append(["float_gt",value,0])
            if pc not in (BASE,VISIBLE,COMPARE,get,recall):
                return
            a,b,c = [machine.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2)]
            ret=0
            if pc==BASE:
                assert (a,b,c)==(obj,param,message)
                result.extend(provider("provider"))
                events.append(["preset_paramChanged",message,*result[:3]])
            elif pc==VISIBLE:
                assert a==obj and len(result)==7
                result[3:6]=[1,result[0],result[1]]
                ret=shown
                events.append(["isVisible",shown])
            elif pc==COMPARE:
                assert (read(a),read(b))==(label,"fsw_load")
                ret=int(read(a)!=read(b))
                events.append(["strcmp",label,"fsw_load"])
            elif pc==get:
                assert a==param
                result[2]+=1
                ret=struct.unpack("<I",struct.pack("<f",value))[0]
                events.append(["getValue",value])
            else:
                assert a==obj
                result[6]=provider("provider-recall")[6]
                events.append(["presets_recall",result[6]])
            machine.reg_write(UC_ARM_REG_R0,ret)
            machine.reg_write(UC_ARM_REG_PC,machine.reg_read(UC_ARM_REG_LR))

        uc.hook_add(UC_HOOK_CODE,hook)
        for reg,a in ((UC_ARM_REG_R0,obj),(UC_ARM_REG_R1,param),(UC_ARM_REG_R2,message),
                      (UC_ARM_REG_SP,0x80E000),(UC_ARM_REG_LR,stop)):
            uc.reg_write(reg,a)
        uc.emu_start(ADDRESS,stop,count=250)
        assert uc.reg_read(UC_ARM_REG_PC)==stop
        out.append({"args":list(args),"expected":result,"events":events})
    return {"elf_sha256":ELF_SHA,"range_sha256":BODY_SHA,"section":".text",
            "address":ADDRESS,"size":SIZE,"offset":OFFSET,
            "slots":slot_evidence,"cases":out}


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe",type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(observe(args.exe),indent=2))
