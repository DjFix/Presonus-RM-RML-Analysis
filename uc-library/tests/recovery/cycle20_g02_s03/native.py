"""Observe the exact offline CS18 meter-scale initializer and its actual arguments."""
import hashlib
import json
from pathlib import Path
import struct
import sys

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_ARM, Uc
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP

source = Path(sys.argv[1])
expected = "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0"
with source.open("rb") as stream:
    assert hashlib.file_digest(stream, "sha256").hexdigest()==expected
    stream.seek(0)
    elf=ELFFile(stream)
    table=elf.get_section_by_name(".symtab")
    name="_Z23__initMeterScaleControlv"
    sym,=table.get_symbol_by_name(name)
    section=elf.get_section(sym["st_shndx"])
    start, size=sym["st_value"],sym["st_size"]
    assert (start, size, sym["st_shndx"], section.name) == (0x69550, 456, 12, ".text")
    offset=start-section["sh_addr"]
    body=section.data()[offset:offset+size]
    assert hashlib.sha256(body).hexdigest() == "f9ceddbba54eb906485388211502840ae8078631b1eac112a6a3a829790d6938"
    assert section["sh_offset"] + offset == 0x61550
    segments=[(row["p_vaddr"],row["p_memsz"],row.data()) for row in elf.iter_segments() if row["p_type"]=="PT_LOAD"]
    destructor_names=[row.name for row in table.iter_symbols() if row["st_value"]==0x64c38 and "MeterScaleControl6Ranges" in row.name]
assert destructor_names
emulator=Uc(UC_ARCH_ARM,UC_MODE_ARM)
lowest=min(x[0] for x in segments)&~4095
highest=max(x[0]+x[1] for x in segments)
emulator.mem_map(lowest,(highest-lowest+4095)&~4095)
for addr,_,data in segments:
    emulator.mem_write(addr,data)
guard, storage, stack, stop = 0x2691a8, 0x2691b0, 0x4000000, 0x5000000
for pos in (stack,stop):
    emulator.mem_map(pos,0x10000)
assert bytes(emulator.mem_read(start,size))==body

def word(address):
    return struct.unpack("<I",emulator.mem_read(address,4))[0]

last_inside=[None]

def observe(uc,pc,size,_):
    if pc==stop:
        uc.emu_stop()
        return
    if start<=pc<start+len(body):
        last_inside[0]=pc
        return
    r0,r1,r2,r3=[uc.reg_read(reg) for reg in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
    call_site=last_inside[0]
    if pc==0x68558:
        assert r0==storage and 1<=r2<=16
        raw_name=bytes(uc.mem_read(r1,32)).split(b"\0",1)[0]
        raw_values=bytes(uc.mem_read(r3,r2*4))
        observed.append(dict(kind="Ranges addRange",caller_site=call_site,receiver=r0,name=raw_name.decode("ascii"),
                             count=r2,values_addr=r3,values=struct.unpack(f"<{r2}i",raw_values),
                             values_sha256=hashlib.sha256(raw_values).hexdigest()))
    elif pc==0xB1C4:
        assert r0==guard
        observed.append({"kind":"guard acquire","previous":word(guard)})
        uc.reg_write(UC_ARM_REG_R0,0 if word(guard)&1 else 1)
    elif pc==0xAB7C:
        assert r0==guard
        uc.mem_write(guard,struct.pack("<I",1))
        observed.append({"kind":"guard release"})
    elif pc==0x69FCC:
        assert (r0,r1)==(storage,0)
        assert [word(storage+idx) for idx in range(0,20,4)]==[0x19bc28,0,0,0,5]
        observed.append({"kind":"pinned Core Vector resize", "count":r1, "typed_native_initial_fields": [word(storage+idx) for idx in range(0,20,4)]})
    elif pc==0xAF24:
        assert (r0,r1)==(storage,0x64c38)
        observed.append({"kind":"lifetime register","receiver":r0,"destructor":r1,"dso":r2})
    else:
        raise ValueError("Unexpected application/runtime boundary: "+hex(pc))
    uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
emulator.hook_add(UC_HOOK_CODE,observe)
runs=[]
for state in ("cold","warm"):
    observed=[]
    emulator.reg_write(UC_ARM_REG_SP,stack+0x8000)
    emulator.reg_write(UC_ARM_REG_LR,stop)
    emulator.emu_start(start,stop,count=3000)
    assert emulator.reg_read(UC_ARM_REG_PC)==stop
    records=[row for row in observed if row["kind"]=="Ranges addRange"]
    assert [row["caller_site"] for row in records]==[0x69584,0x695a8,0x695cc]
    assert [(row["name"],row["count"]) for row in records]==[("default",9),("recordArmed",9),("output",11)]
    assert sum(row["kind"]=="lifetime register" for row in observed)==(1 if state=="cold" else 0)
    runs.append({"state":state,"observed":observed})
evidence={"role":"client","elf":{"path":str(source),"sha256":expected},"mangled":name,
          "address":start,"size":size,"original_sha256":hashlib.sha256(body).hexdigest(),
          "file_offset":section["sh_offset"]+offset,"lifetime_destructor_aliases":destructor_names,
          "cases":runs,"limits":"Exact native application path and real argument reads, with modeled external CCL/runtime boundaries. Host must independently use genuine admitted Ranges and validate the exact data/state."}
print(json.dumps(evidence, indent=2))
