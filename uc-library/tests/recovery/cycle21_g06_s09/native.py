"""Execute either exact Mapping constructor with independently observed boundaries."""
import hashlib
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP

TASK = Path(__file__).parent.name
BASE = Path("temp/recovery-work/reconstruction10x10-20261121/packeting")
PACKET = BASE / "post32-next-batch02/packets" / TASK
INPUTS = BASE / "READ_INPUTS-post32-next-batch02-cycle21_g06-post32-next39-scoped04-dispatch02.json"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fbits(value):
    return struct.unpack("<I", struct.pack("<f", value))[0]


def floating(word):
    return struct.unpack("<f", struct.pack("<I", word))[0]


def load_target():
    request = json.loads((PACKET / "request.json").read_text())
    target, = request["targets"]
    release, = request["work_binding"]["binary_releases"]
    record = json.loads(INPUTS.read_text())[release["original_path"]]
    elf_path = Path(record["frozen_read_path"])
    assert digest(elf_path.read_bytes()) == record["sha256"] == target["original_elf_sha256"]
    with elf_path.open("rb") as stream:
        elf = ELFFile(stream)
        section = elf.get_section(target["section"])
        entry, size = target["address"], target["size"]
        offset = section["sh_offset"] + entry - section["sh_addr"]
        assert 0 <= entry-section["sh_addr"] <= section["sh_size"]-size
        stream.seek(offset)
        body = stream.read(size)
        assert digest(body) in (PACKET/"ELF_CONTEXT.md").read_text()
        segments = [(s["p_vaddr"], s["p_memsz"], s.data()) for s in elf.iter_segments() if s["p_type"] == "PT_LOAD"]
        symbol_table = elf.get_section_by_name(".symtab")
        names = ["_ZN8Presonus7Surface16MappingComponentC1Ev",
                 "_ZN8Presonus7Surface16MappingComponentC2Ev", "_ZN8Presonus10DelayTimerC1Ef"]
        symbols = {s.name: (s["st_value"], s["st_size"]) for s in symbol_table.iter_symbols()
                   if s.name in names}
    return ({"elf": str(elf_path), "target": target, "section": section.name,
             "file_offset": offset, "range_sha256": digest(body)}, segments, symbols)


def make_cpu(segments):
    cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    lo = min(a for a, _, _ in segments)&~0xfff
    hi = max(a+n for a, n, _ in segments)
    cpu.mem_map(lo, (hi-lo+0xfff)&~0xfff)
    for addr, _, data in segments:
        cpu.mem_write(addr, data)
    cpu.mem_map(0x3000000, 0x10000)
    return cpu


def generate():
    proof, segments, symbols = load_target()
    entry, size = proof["target"]["address"], proof["target"]["size"]
    original_constructor = proof["target"]["mangled"]
    assert symbols[original_constructor] == (entry, size)
    one = symbols["_ZN8Presonus7Surface16MappingComponentC1Ev"]
    two = symbols["_ZN8Presonus7Surface16MappingComponentC2Ev"]
    assert one == (0x7f74c, 532) and two == (0x7f960, 532) and one != two
    timer = symbols["_ZN8Presonus10DelayTimerC1Ef"]
    assert timer == (0x11f54, 132)
    proof["constructor_identity"] = {"C1": list(one), "C2": list(two), "native_alias": False}
    cases = []
    for missing_tag in (0, 10004, 10015):
        u = make_cpu(segments)
        obj, arena, allocator, stop = 0x3000000, 0x3001000, 0x3003000, 0x3004000
        u.mem_write(obj, bytes([0x5a])*0x144)
        u.reg_write(UC_ARM_REG_R0,obj)
        u.reg_write(UC_ARM_REG_SP,0x300ff00)
        u.reg_write(UC_ARM_REG_LR,stop)
        descriptors = []
        values = []
        attribute_offsets = []
        timer_inputs = []
        arithmetic = set()
        component_names = []
        def get(addr):
            return struct.unpack("<I",u.mem_read(addr,4))[0]
        def put(addr, number):
            u.mem_write(addr,struct.pack("<I",number))
        def string(addr, size):
            return bytes(u.mem_read(addr,size)).split(b"\0",1)[0].decode("ascii")
        numeric = get(0x2051b0+0x58)
        assert numeric == 0x121198
        def observe(cpu, addr, _size, _context):
            r0,r1,r2 = (cpu.reg_read(reg) for reg in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2))
            if addr == 0x11af30:
                assert r0 == obj
                component_names.append(string(r1,1))
            elif addr == 0x123d2c:
                cpu.reg_write(UC_ARM_REG_R0, allocator)
            elif addr == 0x1239d8:
                assert r1 == allocator
                attribute_offsets.append(r0-obj)
            elif addr == 0xaba0:
                assert r1 == 0 and r2 == 84
                cpu.mem_write(r0, bytes(r2))
            elif addr == 0xb0a4:
                fmt=string(r1,16)
                assert fmt == "number%d"
                rendered=(fmt % r2).encode("ascii")
                cpu.mem_write(r0, rendered+b"\0")
                cpu.reg_write(UC_ARM_REG_R0,len(rendered))
            elif addr == 0x120944:
                assert r0 == obj+0x28 and r2 == 1
                typ, tag = struct.unpack("<II", cpu.mem_read(r1,8))
                descriptor=[tag,string(r1+8,32),typ,*(floating(get(r1+x)) for x in (40,44,48,52,56)),
                            get(r1+60),r2]
                descriptors.append(descriptor)
                param=0 if tag == missing_tag else arena+(tag-10000)*0x20
                if param:
                    put(param,0x2051b0)
                cpu.reg_write(UC_ARM_REG_R0,param)
            elif addr == numeric:
                tag = 10000+(r0-arena)//0x20
                assert r0 == arena+(tag-10000)*0x20 and r2 == 0
                values.append([tag,floating(r1),r2])
            elif addr == timer[0]:
                timer_inputs.append([r0-obj, floating(r1)])
                return
            else:
                if 0x186500 <= addr < 0x188000:
                    arithmetic.add(addr)
                else:
                    assert entry <= addr < entry+size or timer[0] <= addr < timer[0]+timer[1], hex(addr)
                return
            cpu.reg_write(UC_ARM_REG_PC,cpu.reg_read(UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE,observe)
        u.emu_start(entry,stop,count=15000)
        assert u.reg_read(UC_ARM_REG_PC) == stop and u.reg_read(UC_ARM_REG_R0)==obj
        assert component_names==[""] and attribute_offsets==[0xa0,0xc0,0xe0]
        assert len(descriptors)==16 and len(values)==(15 if missing_tag else 16)
        assert len(timer_inputs)==2
        vptrs=[get(obj+i) for i in (0,4,0x84)]
        assert vptrs==[0x19ed50,0x19edb4,0x19edc4]
        assert all(get(obj+i)==0 for i in range(0x88,0xa0,4)) and u.mem_read(obj+0x140,1)==b"\0"
        timers=[]
        for timer_offset,_ in timer_inputs:
            timer_add=obj+timer_offset
            start,duration,elapsed,reciprocal,executing=struct.unpack("<qqqfB",u.mem_read(timer_add,29))
            timers.append([start,duration,elapsed,fbits(reciprocal),executing])
        cases.append({"missing_tag":missing_tag,"component_name":component_names[0],
                      "descriptors":descriptors,"initial_values":values,
                      "attribute_offsets":attribute_offsets,"timer_inputs":timer_inputs,
                      "timers":timers,"native_zeroed_offsets":[*range(0x88,0xa0,4),0x140],
                      "native_vptrs":vptrs,"native_runtime_executed":sorted(arithmetic)})
    proof["cases"]=cases
    return proof


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2))
