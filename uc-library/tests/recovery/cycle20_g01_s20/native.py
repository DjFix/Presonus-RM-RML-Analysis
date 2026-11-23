"""Exact ARM ColorButton draw replay with recorded local output/provider boundaries."""
import argparse
import hashlib
import json
from pathlib import Path
from struct import pack, unpack

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc
from unicorn.arm_const import (UC_ARM_REG_R0 as R0, UC_ARM_REG_R1 as R1,
    UC_ARM_REG_R2 as R2, UC_ARM_REG_R3 as R3, UC_ARM_REG_LR as LR,
    UC_ARM_REG_PC as PC, UC_ARM_REG_SP as SP)

MEM, STACK, STOP = 0x3000000, 0x4000000, 0x5000000
BUTTON, EVENT, RENDERER, MIXER, CHANNEL, STYLE, IMAGE = [
    MEM + 0x100 * i for i in range(7)]
CLIENT = [0, 0, 22, 14]
STYLE_COLOR = 0xff223344
CHANNEL_COLOR = 0xff4973a0
CASES = [
    ("style-alone", False, True, True, 2, True, 3),
    ("no-selection", True, False, True, 2, True, 3),
    ("cast-reject", True, True, False, 2, True, 3),
    ("solid", True, True, True, -2, False, 3),
    ("solid-focus", True, True, True, 2, True, 3),
    ("bitmap-1", True, True, True, 0, False, 1),
    ("bitmap-3-focus", True, True, True, 0, True, 3),
    ("style-focus", True, True, True, 0, True, 0),
]


def sha(p):
    with p.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def capture(elf_path, reference):
    ref = json.loads(reference.read_text())
    identity = ref["original"]
    elf_sha = sha(elf_path)
    assert elf_sha == identity["elf_sha256"]
    start, size = identity["original_address"], identity["original_size"]
    with elf_path.open("rb") as f:
        elf = ELFFile(f)
        symbols = elf.get_section_by_name(".symtab")

        def exact(name):
            syms = symbols.get_symbol_by_name(name)
            assert len(syms) == 1
            sym = syms[0]
            addr, length, si = (sym[k] for k in ("st_value", "st_size", "st_shndx"))
            section = elf.get_section(si)
            relative = addr - section["sh_addr"]
            assert 0 <= relative <= section["sh_size"] - length
            offset = section["sh_offset"] + relative
            f.seek(offset)
            data = f.read(length)
            return dict(address=addr,size=length,file_offset=offset,section=section.name,
                        section_index=si,sha256=hashlib.sha256(data).hexdigest()), data

        exact_range, body = exact(identity["original_mangled"])
        assert (start, size) == (exact_range["address"], exact_range["size"])
        assert all(exact_range[k] == v for k,v in ref["range"].items())
        slots = {int(k): v for k,v in ref["known_virtual_slots"].items()}
        chunks = {start: body}
        points = {}
        for slot in slots.values():
            vtable, data = exact(slot["vtable"])
            assert vtable["sha256"] == slot["vtable_sha256"]
            assert vtable["address"] == slot["vtable_address"]
            assert vtable["file_offset"] == slot["vtable_offset"]
            offset = 8 + slot["slot"]
            assert unpack("<I", data[offset:offset+4])[0] == slot["address"]
            target,_ = exact(slot["mangled"])
            assert target["address"] == slot["address"]
            chunks[vtable["address"]] = data
            points[slot["mangled"]] = vtable["address"] + 8
    assert len(slots) == 5
    original_target = {0x10e9bc,0x10f4b4,0xae58,0x5dac4,0x1864b8,0xf76b4,0x5e578}
    observations = []
    for case in CASES:
        label, mixer, selection, casted, index, focus, frames = case
        uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        pages = {MEM, STACK, STOP} | {a & ~4095 for a in original_target}
        for addr, data in chunks.items():
            pages.update(range(addr & ~4095, ((addr + len(data) - 1) & ~4095) + 4096, 4096))
        pages |= {s["address"] & ~4095 for s in slots.values()}
        for page in sorted(pages):
            uc.mem_map(page,4096)
        for addr,data in chunks.items():
            uc.mem_write(addr,data)

        def put(address, *values):
            uc.mem_write(address,pack("<"+"I"*len(values),*values))

        def get(address, count):
            return list(unpack("<"+"I"*count,uc.mem_read(address,4*count)))

        put(BUTTON+0xe8,MIXER if mixer else 0)
        put(BUTTON+0x58,IMAGE if frames else 0)
        put(BUTTON+0x40,8 if focus else 0)
        put(EVENT, RENDERER)
        put(STYLE, STYLE_COLOR)
        put(IMAGE+8,frames,9,14)
        put(MIXER,next(value for key,value in points.items() if "getSelectedChannel" in key))
        put(RENDERER,next(value for key,value in points.items() if "fillRect" in key))
        trace, output, visited = [], [], set()

        def code(machine, pc, size, _):
            if start <= pc < start+len(body):
                return
            a,b,c,d,lr = [machine.reg_read(r) for r in (R0,R1,R2,R3,LR)]
            site=lr-4
            if site in slots:
                slot=slots[site]
                assert pc == slot["address"]
                visited.add(site)
                if "getSelectedChannel" in slot["mangled"]:
                    assert a==MIXER
                    trace.append("selection")
                    machine.reg_write(R0, CHANNEL if selection else 0)
                elif "drawBitmap" in slot["mangled"]:
                    assert a==RENDERER and c==IMAGE
                    output.append(["bitmap",*get(b,2),*get(d,4)])
                else:
                    assert a==RENDERER
                    output.append(["fill",*get(b,4),get(c,1)[0]])
            else:
                assert pc in original_target
                if pc == 0x10e9bc:
                    assert a==BUTTON
                    put(b,*CLIENT)
                    trace.append("client")
                elif pc == 0x10f4b4:
                    assert a==BUTTON
                    machine.reg_write(R0,STYLE)
                    trace.append("style")
                elif pc == 0xae58:
                    assert a==CHANNEL and {str(b),str(c)}==set(ref["original_RTTI"])
                    machine.reg_write(R0,CHANNEL if casted else 0)
                    trace.append("cast")
                elif pc == 0x5dac4:
                    assert a==CHANNEL
                    machine.reg_write(R0,index & 0xffffffff)
                    trace.append("index")
                elif pc == 0x5e578:
                    assert a==CHANNEL
                    machine.reg_write(R0,CHANNEL_COLOR)
                    trace.append("color")
                elif pc == 0x1864b8:
                    assert a==14 and b==frames>1
                    machine.reg_write(R0,a//b)
                    trace.append("divide")
                elif pc == 0xf76b4:
                    assert a==BUTTON and b==EVENT
                    output.append(["focus"])
            machine.reg_write(PC,lr)

        def write(machine, access, addr, size, value, _):
            assert STACK <= addr < STACK+4096

        for reg,val in ((R0,BUTTON),(R1,EVENT),(LR,STOP),(SP,STACK+0x800)):
            uc.reg_write(reg,val)
        uc.hook_add(UC_HOOK_CODE,code)
        uc.hook_add(UC_HOOK_MEM_WRITE,write)
        uc.emu_start(start,STOP,count=1200)
        assert uc.reg_read(PC)==STOP
        observations.append(dict(case=list(case),trace=trace,output=output,virtual_sites=sorted(visited)))
    assert set().union(*(set(row["virtual_sites"]) for row in observations))==set(slots)
    return dict(elf_sha256=elf_sha,mangled=identity["original_mangled"],exact_range=exact_range,
                reference_sha256=sha(reference),cases=observations)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("elf",type=Path)
    parser.add_argument("reference",type=Path)
    args=parser.parse_args()
    print(json.dumps(capture(args.elf,args.reference),indent=2))
