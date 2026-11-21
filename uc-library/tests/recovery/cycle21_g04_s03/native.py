"""Exact recursive ARM app body with bounded application and CCL boundaries."""
import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import struct
import subprocess

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_ARM
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP,
)

ROOT = Path("/home/rs/projects/opencs/ai-line-analysis")
MAP = ROOT / "temp/recovery-work/reconstruction10x10-20261121/packeting/READ_INPUTS-post39-tail-batch02-cycle21_g04-post39-tail-scoped02-dispatch02.json"
ELF = "rootfs/RML16AI_Rack_13731/home/root/mixer"
ELF_SHA = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
MANGLED = "_ZN8Presonus17LinkableComponent12linkAsMasterERS0_"
ADDRESS,SIZE,OFFSET = 0x82BD8,408,0x7ABD8
BODY_SHA = "f259284343818349c08b3bd130d8fbd9f014d53fddfa8d9f98b672d19a11c69c"


def observe(exe):
    raw = Path(json.loads(MAP.read_text())[ELF]["frozen_read_path"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ELF_SHA
    elf = ELFFile(BytesIO(raw))
    symbols = elf.get_section_by_name(".symtab")
    sym = symbols.get_symbol_by_name(MANGLED)[0]
    assert (sym["st_value"],sym["st_size"],sym["st_shndx"]) == (ADDRESS,SIZE,12)
    section = elf.get_section(sym["st_shndx"])
    assert section.name == ".text"
    assert section["sh_offset"] + ADDRESS - section["sh_addr"] == OFFSET
    body = raw[OFFSET:OFFSET+SIZE]
    assert hashlib.sha256(body).hexdigest() == BODY_SHA
    slot_evidence = {}
    table = symbols.get_symbol_by_name("_ZTVN8Presonus17LinkableComponentE")[0]
    for offset,name in ((0,"_ZN8Presonus17LinkableComponent6castToEi"),
                        (0x14,"_ZNK4Core8Portable9Component9findChildEPKc")):
        address = table["st_value"]+8+offset
        backing = elf.get_section(table["st_shndx"])
        value, = struct.unpack_from("<I",backing.data(),address-backing["sh_addr"])
        assert symbols.get_symbol_by_name(name)[0]["st_value"]==value
        slot_evidence[str(offset)] = {"address":address,"value":value,"mangled":name}
    provider = list(map(int,subprocess.check_output(
        [str(exe.resolve()),"provider","0"],text=True).split()))
    assert provider == [21,1,90,0], provider

    rows=[]
    names=("left","right","child","child","leaf","leaf","uncast","unmatched")
    children={0:[None,6,7,2],1:[3],2:[4],3:[5]}
    for scenario in range(6):
        uc=Uc(UC_ARCH_ARM,UC_MODE_ARM)
        uc.mem_map(0x82000,0x1000)
        uc.mem_write(ADDRESS,body)
        for page in (0x119000,0x10E000):
            uc.mem_map(page,0x1000)
        uc.mem_map(0x800000,0x20000)
        objects=[0x801000+0x400*i for i in range(8)]
        ids={a:i for i,a in enumerate(objects)}
        vtable,lookup,cast,stop=0x80A000,0x80B000,0x80B004,0x81F000
        param_ids={}
        params={}
        values={}
        edits=[0]*8
        storage=[[90+i,int(i%2==0),int(i%2==1)] for i in range(8)]
        calls=[]
        queries=[]
        stack=[]
        lock=0
        def word(a,v): uc.mem_write(a,struct.pack("<I",v))
        def get(a): return struct.unpack("<I",uc.mem_read(a,4))[0]
        def set_byte(a,v): uc.mem_write(a,bytes([v]))
        def get_byte(a): return uc.mem_read(a,1)[0]
        word(vtable,cast)
        word(vtable+0x14,lookup)
        for i,obj in enumerate(objects):
            uc.mem_write(obj+8,names[i].encode()+b"\0")
            word(obj,vtable)
            set_byte(obj+0x8C,int(i%2==0))
            set_byte(obj+0x8D,int((i%2==0 and 0<i<6) or (i==0 and scenario!=1)))
            tag_order=[11,13,12] if i%2==0 else [11,13]
            array=obj+0x110
            word(obj+0x34,array);word(obj+0x38,len(tag_order))
            for idx,tag in enumerate(tag_order):
                param,info=obj+0x140+0x80*idx,obj+0x160+0x80*idx
                word(array+4*idx,param);word(param+12,info)
                word(info+4,tag);word(info+0x3C,8 if tag!=13 else 0)
                params[i,tag]=param
                param_ids[param]=(i,tag)
                values[i,tag]=21+i if tag==11 else -20-i if tag==13 else 0
            child_array=obj+0x100
            word(obj+0x58,child_array);word(obj+0x5C,len(children.get(i,[])))
            for k,j in enumerate(children.get(i,[])):
                word(child_array+4*k,objects[j] if j is not None else 0)
        if scenario==2: word(objects[0]+0x88,objects[1])
        if scenario==3: word(objects[1]+0x88,objects[0])
        if scenario==4: word(objects[2]+0x88,objects[3])

        def hook(machine,pc,_,_unused):
            nonlocal lock
            a,b,c,d=[machine.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
            if pc==ADDRESS:
                stack.append((ids[a],ids[b]))
                calls.append(["enter",*stack[-1]])
            elif pc==0x82CB0:
                calls.append(["leave",*stack.pop()])
            if pc not in (cast,lookup,0x119C4C,0x8264C,0x10E384,0x82B44,0x10E460):
                return
            result=0
            if pc==cast:
                assert b==1282304865
                i=ids[a]
                queries.append(i)
                result=0 if i==6 or (i==3 and scenario==5) else a
                calls.append(["cast",i,bool(result)])
            elif pc==lookup:
                name=bytes(machine.mem_read(b,32)).split(b"\0",1)[0].decode()
                targets=children.get(ids[a],[])
                matched=next((i for i in targets if i is not None and names[i]==name),None)
                result=objects[matched] if matched is not None else 0
                calls.append(["find_child",ids[a],name,matched])
            elif pc==0x119C4C:
                result=params.get((ids[a],b),0)
                calls.append(["by_tag",ids[a],b,bool(result)])
            elif pc==0x8264C:
                source,tag=param_ids[b]
                dest,dest_tag=param_ids[c]
                assert d==1 and source==ids[a] and tag==dest_tag==11 and lock==0
                edits[dest]+=int(values[dest,tag]!=values[source,tag])*provider[1]
                values[dest,tag]=values[source,tag]
                calls.append(["sync",source,dest,tag,d])
            elif pc==0x10E384:
                assert a==4803568 and lock==0
                lock+=1
                calls.append(["lock"])
            elif pc==0x82B44:
                assert lock==1
                dest=ids[a]
                source=ids[b-0x90]
                storage[dest]=list(storage[source])
                calls.append(["alternate",source,dest])
            else:
                assert a==4803568 and lock==1
                lock-=1
                calls.append(["unlock"])
            machine.reg_write(UC_ARM_REG_R0,result)
            machine.reg_write(UC_ARM_REG_PC,machine.reg_read(UC_ARM_REG_LR))

        uc.hook_add(UC_HOOK_CODE,hook)
        for reg,v in ((UC_ARM_REG_R0,objects[0]),(UC_ARM_REG_R1,objects[1]),
                      (UC_ARM_REG_SP,0x81E000),(UC_ARM_REG_LR,stop)):
            uc.reg_write(reg,v)
        uc.emu_start(ADDRESS,stop,count=2200)
        assert uc.reg_read(UC_ARM_REG_PC)==stop and not stack and lock==0
        output=[]
        for i,obj in enumerate(objects[:6]):
            output.extend([ids.get(get(obj+0x88),-1),get_byte(obj+0x8C),
                           values[i,11],values[i,13],edits[i],*storage[i]])
        rows.append({"scenario":scenario,"queries":queries,"expected":output,"calls":calls})
    return {"elf_sha256":ELF_SHA,"body_sha256":BODY_SHA,"section":".text",
            "offset":OFFSET,"address":ADDRESS,"size":SIZE,"slots":slot_evidence,
            "actual_provider_probe":provider,"cases":rows}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe",type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(observe(args.exe),indent=2))
