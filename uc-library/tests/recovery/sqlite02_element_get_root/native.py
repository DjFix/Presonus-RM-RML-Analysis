"""Replay exact offline Element code on initialized ARM receiver trees."""
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sqlite02_element_complete_construct"))
from native import (Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE,
                    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
                    UC_ARM_REG_SP, ELFFile, LIBC, PAGE, TREE, HEAP, STACK, STOP,
                    NAME, PREFIX, digest, provider)
from unicorn.arm_const import UC_ARM_REG_R2

CASES = {
    "get_root": [[0], [1], [2], [3]],
    "is_element_class": [[None], [""], ["match"], ["Match"], ["no"]],
    "load_local_attributes": [[None], [""], ["live"], ["x"*63], ["x"*80]],
    "save_local_attributes": [[""], ["live"], ["x"*63]],
}


def execute(original, task, root, exe):
    path = root / original["elf_path"]
    raw = path.read_bytes()
    assert digest(raw) == original["elf"]
    with path.open("rb") as stream:
        elf = ELFFile(stream)
        symbols = {symbol.name: symbol for symbol in elf.get_section_by_name(".symtab").iter_symbols()}

        def bind(name):
            sym = symbols[name]
            index = sym["st_shndx"]
            sec = elf.get_section(index)
            address, size = sym["st_value"], sym["st_size"]
            offset = sec["sh_offset"] + address - sec["sh_addr"]
            assert sec["sh_offset"] <= offset <= offset + size <= sec["sh_offset"] + sec["sh_size"]
            data = raw[offset:offset + size]
            return dict(mangled=name, address=address, size=size, section=index,
                        section_name=sec.name, file_offset=offset,
                        range_sha256=digest(data), range_hex=data.hex())

        target = bind(original["mangled"])
        assert all(original[key] == value for key, value in target.items())
        ctor = bind(PREFIX + "C1ERKNS0_11MetaElementE")
        d0 = bind(PREFIX + "D0Ev")
        adopt = bind(PREFIX + "8addChildEPS1_")
        meta_cmp = bind("_ZNK8Presonus2UC11MetaElement7isClassEPKc")
        resize = bind("_ZN4Core6VectorIPN8Presonus2UC7ElementEE6resizeEi")
        vector_d1 = bind("_ZN4Core6VectorIPN8Presonus2UC7ElementEED1Ev")
        string_ctor = bind("_ZN4Core13CStringBufferILi64EEC1EPKc")
        string_assign = bind("_ZN4Core13CStringBufferILi64EEaSEPKc")
        vtable = bind("_ZTVN8Presonus2UC7ElementE")
        plt = elf.get_section_by_name(".plt")
        rel = elf.get_section_by_name(".rel.plt")
        dynsym = elf.get_section(rel["sh_link"])
        entries = {dynsym.get_symbol(rec["r_info_sym"]).name: plt["sh_addr"] + 20 + i*12
                   for i, rec in enumerate(rel.iter_relocations())}
        segments = [(seg["p_vaddr"], seg.data(), seg["p_memsz"])
                    for seg in elf.iter_segments() if seg["p_type"] == "PT_LOAD"]

    results = []
    bodies = (ctor, d0, adopt, meta_cmp, target)
    for case in CASES[task]:
        uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        end = max(a + n for a, _, n in segments)
        uc.mem_map(0, (end + PAGE - 1) & -PAGE)
        for a, data, _ in segments:
            uc.mem_write(a, data)
        uc.mem_map(TREE, 10*PAGE)
        for a in (STACK, STOP, NAME):
            uc.mem_map(a, PAGE)
        nodes = {TREE + PAGE*i: i for i in range(8)}
        dest = TREE
        metadata, attributes, vtab = NAME + 0x200, NAME + 0x300, NAME + 0x400
        override, lookup, store_name = STOP + 4, STOP + 8, STOP + 12
        blocks = {}
        live = set()
        used = 0
        armed = False
        cleanup = False
        calls, writes, pcs, freed = [], [], [], []

        def get(a):
            return int.from_bytes(uc.mem_read(a, 4), "little")

        def put(a, value):
            uc.mem_write(a, struct.pack("<I", value))

        def string(a):
            if not a:
                return None
            return bytearray(uc.mem_read(a, 128)).split(b"\0", 1)[0].decode()

        def put_string(a, value):
            uc.mem_write(a, value.encode() + b"\0")

        def ret(value):
            uc.reg_write(UC_ARM_REG_R0, value)
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

        def call(body, x, y=0):
            for reg, value in ((UC_ARM_REG_SP, STACK+PAGE-16), (UC_ARM_REG_LR, STOP),
                               (UC_ARM_REG_R0, x), (UC_ARM_REG_R1, y)):
                uc.reg_write(reg, value)
            uc.emu_start(body["address"], STOP, count=20000)
            assert uc.reg_read(UC_ARM_REG_PC) == STOP
            return uc.reg_read(UC_ARM_REG_R0)

        def event(*args):
            if armed:
                calls.append(list(args))

        def on_code(machine, pc, _, __):
            nonlocal used
            x = machine.reg_read(UC_ARM_REG_R0)
            y = machine.reg_read(UC_ARM_REG_R1)
            z = machine.reg_read(UC_ARM_REG_R2)
            if pc == string_ctor["address"]:
                assert not y
                assert provider(exe,"provider-string","<null>") == ["0"]
                put_string(x, "")
                ret(x)
            elif pc == string_assign["address"]:
                assert x == dest + 4
                text = string(y)
                length, *value = provider(exe,"provider-string",text if text is not None else "<null>")
                assert len(value[0] if value else "") == int(length)
                put_string(x, value[0] if value else "")
                event("pinned CString64 assignment", text, int(length))
                ret(x)
            elif pc == resize["address"]:
                node = x - 0x4c
                assert node in live
                count, cap = get(node+0x54), get(node+0x58)
                new, = map(int, provider(exe, "provider-capacity", cap, y))
                if cap != new:
                    old = blocks.pop(node, 0)
                    if new:
                        used += 1
                        block = HEAP + PAGE*used
                        uc.mem_map(block, PAGE)
                        if old:
                            uc.mem_write(block, bytes(uc.mem_read(old, 4*count)))
                        blocks[node] = block
                    else:
                        block = 0
                        put(node+0x54, 0)
                    if old:
                        uc.mem_unmap(old, PAGE)
                    put(node+0x50, block)
                    put(node+0x58, new)
                event("pinned Vector resize", nodes[node], y, new)
                ret(1)
            elif pc == vector_d1["address"]:
                node = x - 0x4c
                old = blocks.pop(node, 0)
                if old:
                    uc.mem_unmap(old, PAGE)
                ret(x)
            elif pc == entries["_ZdlPv"]:
                assert cleanup and x in live
                live.remove(x)
                freed.append(nodes[x])
                ret(0)
            elif pc == entries["strcmp"]:
                lhs, rhs = string(x), string(y)
                event("native strcmp", lhs, rhs)
                ret(LIBC.strcmp(lhs.encode(), rhs.encode()) & 0xffffffff)
            elif pc == override:
                assert x == dest
                event("root slot override", nodes[x])
                ret(x)
            elif pc == lookup:
                assert x == attributes
                key = string(y)
                event("attribute lookup slot 0", key)
                text, = provider(exe, "provider-lookup", key, case[0] if case[0] is not None else "<null>")
                if text == "<null>":
                    ret(0)
                else:
                    put_string(NAME, text[1:])
                    ret(NAME)
            elif pc == store_name:
                assert x == attributes and z == dest + 4
                event("attribute store slot 1", string(y), string(z))
                ret(0)
            else:
                assert any(b["address"] <= pc < b["address"] + b["size"] for b in bodies), hex(pc)
                if armed:
                    pcs.append(pc)
                    if pc == target["address"] and task == "get_root":
                        event("base root slot", nodes[x])
                    if pc == meta_cmp["address"]:
                        assert x == metadata
                        event("metadata borrowed identity", string(y))

        def on_write(_, mode, address, size, value, aux):
            if armed and not STACK <= address < STACK + PAGE:
                page = address & -PAGE
                owner = nodes[page] if page in nodes else {b: nodes[n] for n,b in blocks.items()}[page]
                writes.append([owner, page in nodes, address - page, size, nodes.get(value,value)])

        def construct(node):
            live.add(node)
            assert call(ctor, node, metadata) == node

        def roster(node):
            return [nodes[get(get(node+0x50) + i*4)] for i in range(get(node+0x54))]

        uc.hook_add(UC_HOOK_CODE, on_code)
        uc.hook_add(UC_HOOK_MEM_WRITE, on_write)
        put_string(NAME + 0x100, "match")
        put(metadata, NAME + 0x100)
        construct(dest)
        second = 0
        receiver = dest
        if task == "get_root":
            depth = min(case[0], 2)
            if case[0] == 3:
                original_table = get(dest)
                uc.mem_write(vtab, bytes(uc.mem_read(original_table, 16)))
                assert get(vtab+8) == target["address"]
                put(vtab+8, override)
                put(dest, vtab)
            for i in range(depth):
                child = TREE + (i+1)*PAGE
                construct(child)
                call(adopt, receiver, child)
                receiver = child
        elif task == "is_element_class":
            if case[0] is not None:
                put_string(NAME, case[0])
                second = NAME
        else:
            put(attributes, vtab)
            put(vtab, lookup)
            put(vtab + 4, store_name)
            put_string(dest + 4, "previous" if task.startswith("load") else case[0])
            second = attributes
        armed = True
        result = call(target, receiver, second)
        armed = False
        if task == "get_root":
            output = nodes[result]+1 if result else 0
        elif task == "is_element_class":
            output = result
        elif task.startswith("load"):
            assert calls[0][:2] == ["attribute lookup slot 0", "id"]
            output = [result, string(dest+4)]
        else:
            assert calls == [["attribute store slot 1", "id", case[0]]] and not writes
            output = [result, calls[0][2]]
        results.append(dict(inputs=case, output=output, calls=calls, writes=writes, executed_pcs=pcs))
    return dict(original=original, supporting={b["mangled"]: b for b in
                (*bodies, resize, vector_d1, string_ctor, string_assign, vtable)}, cases=results)


if __name__ == "__main__":
    context, root, exe = map(Path, sys.argv[1:])
    packet = json.loads(context.read_text())
    task = packet["task"]["id"].removeprefix("sqlite02_element_")
    print(json.dumps([execute(row["original"], task, root, exe) for row in packet["originals"]], indent=2))
