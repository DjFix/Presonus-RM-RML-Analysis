"""Independent ARM application replay with modeled typed CCL call boundaries."""

import hashlib
import io
import json
from pathlib import Path
import struct
import sys

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import (UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0,
                               UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
                               UC_ARM_REG_SP)

ROOT = 0x800000
STOP = 0x820000
STACK = 0x830000
VIRTUALS = 0x840000
HEAP = 0x850000
REGS = (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)
SCALAR = ("gain", 3, 2.5, False)
STRING = ("title", 4, "hello", False)
COLOR = ("color", 6, 0xf1234567, False)
PRIVATE = ("private", 3, 42, True)
EMPTY = ("empty", True, (), ())
LEAF = ("leaf", True, (SCALAR,), ())
FOREIGN = ("foreign", False, (SCALAR,), ())
BRANCH = ("branch", True, (), (LEAF,))
SCENARIOS = {
    "empty": ("root", True, (), ()),
    "private": ("root", True, (PRIVATE,), ()),
    "values": ("root", True, (SCALAR, STRING, COLOR, PRIVATE), ()),
    "children": ("root", True, (), (EMPTY, FOREIGN, BRANCH)),
    "mixed": ("root", True, (STRING,), (EMPTY, LEAF)),
    "pruned": ("root", True, (), (EMPTY, FOREIGN)),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run(image, elf, original, ranges, scenario):
    start = original["address"]
    sym, = elf.get_section_by_name(".symtab").get_symbol_by_name(original["mangled"])
    index = sym["st_shndx"]
    section = elf.get_section(index)
    offset = section["sh_offset"] + start - section["sh_addr"]
    assert section.name == ".text" and index == original["section"]
    assert (sym["st_value"], sym["st_size"], offset) == (start, original["size"], original["file_offset"])
    code = image[offset:offset+original["size"]]
    assert sha(code) == original["range_sha256"] and code.hex() == original["range_hex"]

    u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    u.mem_map(start & ~4095, 8192)
    u.mem_write(start, code)
    for p in (ROOT, STOP, STACK, VIRTUALS):
        u.mem_map(p, 4096)
    u.mem_map(HEAP, 0x20000)
    u.mem_write(VIRTUALS, struct.pack("<I", 0xe12fff1e) * 1024)
    trace, writes = [], []
    components, parameters, attributes, slots = {}, {}, {}, {}
    next_pointer = HEAP

    def allocate(size=256):
        nonlocal next_pointer
        base = next_pointer
        next_pointer += (size + 15) & ~15
        assert next_pointer < HEAP+0x20000
        return base

    def words(address, *values):
        if values:
            u.mem_write(address, struct.pack(f"<{len(values)}I", *values))

    def text(address, value):
        u.mem_write(address, value.encode()+b"\0")

    def cstr(address):
        value = bytearray()
        for off in range(256):
            ch = u.mem_read(address+off, 1)[0]
            if not ch:
                return value.decode()
            value.append(ch)
        raise ValueError(address)

    def parameter(spec):
        name, kind, value, private = spec
        address = allocate()
        info = allocate()
        vtable = allocate()
        words(address, vtable)
        words(vtable, VIRTUALS)
        words(vtable+0x60, VIRTUALS+4)
        words(vtable+0x70, VIRTUALS+8)
        words(address+12, info)
        words(info, kind)
        text(info+8, name)
        words(info+0x3c, 4 if private else 0)
        parameters[address] = spec
        return address

    def component(tree):
        name, is_client, params, children = tree
        address = allocate()
        vtable = allocate()
        child_list = allocate()
        words(address,vtable)
        words(vtable,VIRTUALS)
        text(address+8,name)
        words(address+0x58,child_list,len(children))
        words(child_list,*(component(child) for child in children))
        components[address] = (name, is_client, [parameter(p) for p in params])
        return address

    def new_attributes():
        a = allocate()
        attributes[a] = {}
        words(a+8, ROOT+0x200)
        return a

    def set_slot(pointer, value):
        container, name = slots[pointer]
        attributes[container][name] = value

    output = new_attributes()
    root = component(scenario)
    native_inputs = [(p,bytes(u.mem_read(p, 256))) for p in (*components, *parameters)]
    targets = {}
    mapped = {start & ~4095, (start & ~4095)+4096}
    for site in ranges:
        if site["target"] in ("values", "children"):
            address = site["address"]
            value = site["target"].encode()+b"\0"
            for segment in elf.iter_segments(type="PT_LOAD"):
                delta=address-segment["p_vaddr"]
                if 0<=delta<=segment["p_filesz"]-len(value):
                    file_offset=segment["p_offset"]+delta
                    assert image[file_offset:file_offset+len(value)]==value
                    break
            else:
                raise AssertionError(address)
            page = address & ~4095
            if page not in mapped:
                u.mem_map(page,4096)
                mapped.add(page)
            u.mem_write(address,value)
    for site in ranges:
        target = site["target"]
        if target.startswith(("Core::", "__aeabi")):
            address = site["address"]
            # Independently match the original instruction and signed ARM branch.
            off = site["offset"]
            word, = struct.unpack_from("<I",code,off)
            assert word >> 24 == 0xeb
            immediate = word & 0xffffff
            if immediate & 0x800000:
                immediate -= 0x1000000
            assert start+off+8+4*immediate==address
            page = address & ~4095
            if page not in mapped:
                u.mem_map(page,4096)
                mapped.add(page)
            u.mem_write(address,struct.pack("<I",0xe12fff1e))
            targets[address] = target

    def callback(machine, pc, size, user):
        if pc == start:
            trace.append(["collect",components[machine.reg_read(REGS[2])][0]])
            return
        target = targets.get(pc)
        if target is None and pc not in (VIRTUALS,VIRTUALS+4,VIRTUALS+8):
            return
        a,b,c,d = (machine.reg_read(r) for r in REGS)
        result = None
        if pc == VIRTUALS:
            trace.append(["cast",b])
            if a in components:
                assert b == 0x436c436f
                result = a if components[a][1] else 0
            else:
                assert b == 0x43506172 and a in parameters
                result = a if parameters[a][1]==6 else 0
        elif pc == VIRTUALS+4:
            trace.append(["numeric",parameters[a][0]])
            result, = struct.unpack("<I",struct.pack("<f",parameters[a][2]))
        elif pc == VIRTUALS+8:
            trace.append(["string",parameters[a][0]])
            assert c==256
            text(b,parameters[a][2][:255])
        elif "countParameters" in target:
            result = len(components[a][2])
            trace.append(["count",components[a][0],result])
        elif "getParameterAt" in target:
            result = components[a][2][b]
            trace.append(["parameter",components[a][0],b])
        elif "getColor()" in target:
            result = parameters[a][2]
            trace.append(["color",parameters[a][0],result])
        elif "addNew" in target:
            name = cstr(b)
            result = allocate()
            slots[result] = (a,name)
            attributes[a][name] = None
            words(a+0x14,len(attributes[a]))
            trace.append(["add",name])
        elif "makeAttributes" in target:
            assert b == ROOT+0x200
            result = new_attributes()
            set_slot(a, ("tree",result))
            trace.append(["tree",slots[a][1]])
        elif "::remove(" in target:
            name = cstr(b)
            result = int(name in attributes[a])
            attributes[a].pop(name,None)
            words(a+0x14,len(attributes[a]))
            trace.append(["remove",name])
        elif "Buffer<256>" in target:
            assert b == 0
            text(a,"")
        elif "__aeabi_f2d" in target:
            value, = struct.unpack("<f",struct.pack("<I",a))
            lo, hi = struct.unpack("<II",struct.pack("<d",value))
            result = lo
            machine.reg_write(REGS[1],hi)
        elif "::set(" in target:
            if target.endswith("(double)"):
                value, = struct.unpack("<d",struct.pack("<II",c,d))
                set_slot(a,("float",value))
            elif target.endswith("(long long)"):
                value, = struct.unpack("<q",struct.pack("<II",c,d))
                set_slot(a,("int",value))
            else:
                assert target.endswith("(char const*, bool)") and c==0
                set_slot(a,("string",cstr(b)))
            trace.append(["set",slots[a][1]])
        else:
            raise AssertionError(target)
        if result is not None:
            machine.reg_write(REGS[0],result)

    def flatten(container,prefix=""):
        result=[]
        for key,(kind,value) in attributes[container].items():
            path=prefix+"/"+key
            if kind == "tree":
                result.append("tree "+path)
                result.extend(flatten(value,path))
            else:
                result.append(f"{kind} {path} {value}")
        return result

    u.hook_add(UC_HOOK_CODE,callback)
    u.hook_add(UC_HOOK_MEM_WRITE,lambda mc,ac,ad,sz,v,s:writes.append((ad,sz)))
    for i,val in enumerate((ROOT,output,root)):
        u.reg_write(REGS[i],val)
    u.reg_write(UC_ARM_REG_LR,STOP)
    u.reg_write(UC_ARM_REG_SP,STACK+2048)
    u.emu_start(start,STOP,count=20000)
    assert u.reg_read(UC_ARM_REG_PC)==STOP
    assert all(bytes(u.mem_read(a,256))==b for a,b in native_inputs)
    assert all(STACK<=a<STACK+4096 or HEAP<=a<next_pointer for a,n in writes)
    returned=u.reg_read(REGS[0])
    assert returned in (0,1)
    return dict(result=returned, attributes=flatten(output), call_trace=trace)


packet=json.loads(Path(sys.argv[1]).read_bytes())
binding=packet["task"]["review"]["equivalence"]
evidence=Path(binding["path"]).read_bytes()
assert sha(evidence)==binding["sha256"]
ranges=json.loads(evidence)["normalized"]["per_role_addresses"]
result=[]
for idx,item in enumerate(packet["originals"]):
    original=item["original"]
    blob=Path(original["elf_path"]).read_bytes()
    assert sha(blob)==original["elf"]
    elf=ELFFile(io.BytesIO(blob))
    cases={name:run(blob,elf,original,ranges[idx],case) for name,case in SCENARIOS.items()}
    result.append(dict(original=original,cases=cases))
assert result[0]["cases"]==result[1]["cases"]
print(json.dumps(result,indent=2))
