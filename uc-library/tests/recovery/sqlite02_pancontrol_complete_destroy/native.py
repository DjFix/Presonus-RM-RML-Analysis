"""Execute exact CS18 destructor and setter ranges with bounded provider hooks."""
import hashlib
import io
import json
from pathlib import Path
import struct

from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import (
    UC_ARM_REG_PC, UC_ARM_REG_LR, UC_ARM_REG_SP, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2,
)

ROOT = Path(__file__).resolve().parents[4]
PACKETS = Path("temp/recovery-work/sqlite-issued/packet")
SETTERS = ("setStereoParam", "setLinkParam", "setChannelNumberParam",
           "setRightSideParam", "setStereoPanParam")
OFFSETS = (0x68, 0x64, 0x6c, 0x70, 0x74)
REMOVE = "_ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE"
ADD = "_ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE"
INVALIDATE = "_ZN4Core8Portable4View10invalidateEv"
CONTROL = "_ZN4Core8Portable7ControlD2Ev"
CHANGED = "_ZN8Presonus10PanControl12paramChangedEPN4Core8Portable9ParameterEi"
BASE_CHANGED = "_ZN4Core8Portable7Control12paramChangedEPNS0_9ParameterEi"
VTABLE = "_ZTVN8Presonus10PanControlE"
CASES = (
    (0, 0, 0, 0, 0), (31, 1, 0, 0, 0), (21, 1, 0, 0, 0),
    (31, 1, 1, 0, 0), (31, 1, 2, 0, 0), (31, 1, 0, 1, 0),
    (31, 1, 0, 2, 0), (31, 1, 0, 3, 0), (0, 0, 0, 0, 1),
)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def generate(task):
    packet = json.loads((ROOT / PACKETS / task / "CONTEXT.json").read_text())
    original = packet["originals"][0]["original"]
    evidence = packet["task"]["review"]["evidence"][0]
    assert digest((ROOT / evidence["path"]).read_bytes()) == evidence["sha256"]
    raw = (ROOT / original["elf_path"]).read_bytes()
    assert digest(raw) == original["elf"]
    elf = ELFFile(io.BytesIO(raw))
    assert elf.little_endian and elf["e_machine"] == "EM_ARM"
    symbols = elf.get_section_by_name(".symtab")

    def lookup(name):
        sym, = symbols.get_symbol_by_name(name)
        section = elf.get_section(sym["st_shndx"])
        delta = sym["st_value"] - section["sh_addr"]
        size = sym["st_size"]
        assert 0 <= delta <= section["sh_size"] - size
        offset = section["sh_offset"] + delta
        body = raw[offset:offset + size]
        return dict(mangled=name, address=sym["st_value"], size=size,
                    section=sym["st_shndx"], section_name=section.name,
                    file_offset=offset, range_sha256=digest(body), range_hex=body.hex())

    target = lookup(original["mangled"])
    assert all(original[k] == value for k, value in target.items())
    remove = lookup(REMOVE)
    add = lookup(ADD)
    control = lookup(CONTROL)
    invalidate = lookup(INVALIDATE)
    table = lookup(VTABLE)
    changed = lookup(CHANGED)
    base_changed = lookup(BASE_CHANGED)
    setters = [lookup(f"_ZN8Presonus10PanControl{len(name)}{name}EPN4Core8Portable9ParameterE")
               for name in SETTERS]
    cap = Cs(CS_ARCH_ARM, CS_MODE_ARM)

    def instructions(record):
        return list(cap.disasm(bytes.fromhex(record["range_hex"]), record["address"]))

    for setter, offset in zip(setters, OFFSETS, strict=True):
        assert any(i.mnemonic == "ldr" and i.op_str == f"r0, [r0, #{offset:#x}]"
                   for i in instructions(setter))
        assert [int(i.op_str[1:], 16) for i in instructions(setter) if i.mnemonic == "bl"] == [
            remove["address"], add["address"]]
    deleting = "D0Ev" in target["mangled"]
    calls = [int(i.op_str[1:], 16) for i in instructions(target) if i.mnemonic == "bl"]
    assert calls[:6] == [remove["address"]] * 5 + [control["address"]]
    address_point = table["address"] + 8
    words = struct.unpack("<" + "I" * (table["size"] // 4), bytes.fromhex(table["range_hex"]))
    if "D2Ev" not in target["mangled"]:
        slot = 4 if deleting else 3
        assert words[slot] == target["address"], words
    assert struct.unpack_from("<I", bytes.fromhex(target["range_hex"]), target["size"] - 8)[0] == address_point
    deallocator = None
    if deleting:
        plt = elf.get_section_by_name(".plt")
        displacement = calls[6] - plt["sh_addr"]
        index, remainder = divmod(displacement - 20, 12)
        assert not remainder and index >= 0
        rels = elf.get_section_by_name(".rel.plt")
        rel = rels.get_relocation(index)
        assert elf.get_section(rels["sh_link"]).get_symbol(rel["r_info_sym"]).name == "_ZdlPv"
        offset = plt["sh_offset"] + displacement
        deallocator = dict(mangled="_ZdlPv", address=calls[6], file_offset=offset,
                           got=rel["r_offset"], sha256=digest(raw[offset:offset + 12]))
    return dict(original=original, setters=setters, remove=remove, add=add,
                base=control, changed=changed, base_changed=base_changed, invalidate=invalidate, vtable=table, deallocator=deallocator,
                cases=[execute(case, target, setters, remove, add, control, deallocator,
                               address_point, invalidate, changed, base_changed) for case in CASES])


def execute(case, target, setters, remove, add, control, deallocator, address_point, invalidate, changed, base_changed):
    mask, primary, replaced, destroyed, borrowed = case
    receiver, stack, pool, stop = 0x1000000, 0x2000000, 0x3000000, 0x4000000
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    for address, size in ((0x8000, 0x210000), (receiver, 4096), (stack, 4096), (pool, 4096)):
        uc.mem_map(address, size)

    def put(address, val):
        uc.mem_write(address, struct.pack("<I", val))

    def get(address):
        return struct.unpack("<I", uc.mem_read(address, 4))[0]

    for record in [target, changed, *setters]:
        uc.mem_write(record["address"], bytes.fromhex(record["range_hex"]))
    put(receiver, address_point)
    provider = [pool + 0x10 * (i + 1) for i in range(7)]
    registered = []
    events, trace, writes, setup = [], [], [], []
    running_destructor = False
    live = True
    death = []

    def visit(emu, pc, size, _):
        nonlocal live
        r0 = emu.reg_read(UC_ARM_REG_R0)
        r1 = emu.reg_read(UC_ARM_REG_R1)
        lr = emu.reg_read(UC_ARM_REG_LR)
        if pc == remove["address"] or pc == add["address"]:
            assert r1 == receiver + 0x44 and r0 in provider
            number = provider.index(r0) + 1
            if pc == add["address"]:
                assert not running_destructor
                registered.append(number)
                setup.append(["add", number])
            else:
                registered.remove(number)
                (events if running_destructor else setup).append(["remove", number])
        elif pc == invalidate["address"]:
            assert not running_destructor and r0 == receiver
        elif pc == base_changed["address"]:
            assert not running_destructor and r0 == receiver and r1 in provider
            assert emu.reg_read(UC_ARM_REG_R2) == 5
            death.append(provider.index(r1) + 1)
        elif pc == control["address"]:
            assert running_destructor and r0 == receiver and not registered
            events.append(["base", primary])
        elif deallocator and pc == deallocator["address"]:
            assert running_destructor and r0 == receiver and live and events[-1][0] == "base"
            events.append(["delete", 1])
            live = False
            emu.mem_unmap(receiver, 4096)
        else:
            assert any(r["address"] <= pc < r["address"] + r["size"] for r in [target, changed, *setters])
            if running_destructor:
                trace.append(pc - target["address"])
            return
        emu.reg_write(UC_ARM_REG_PC, lr)

    def write(emu, access, address, size, value, _):
        if running_destructor and not stack <= address < stack + 4096:
            writes.append([address, size, value])

    uc.hook_add(UC_HOOK_CODE, visit)
    uc.hook_add(UC_HOOK_MEM_WRITE, write)

    def run(entry, param=0, message=0):
        uc.reg_write(UC_ARM_REG_SP, stack + 0x800)
        uc.reg_write(UC_ARM_REG_R0, receiver)
        uc.reg_write(UC_ARM_REG_R1, param)
        uc.reg_write(UC_ARM_REG_R2, message)
        uc.reg_write(UC_ARM_REG_LR, stop)
        uc.emu_start(entry, stop, count=256)
        assert uc.reg_read(UC_ARM_REG_PC) == stop
        assert uc.reg_read(UC_ARM_REG_SP) == stack + 0x800

    for index, setter in enumerate(setters):
        if mask & (1 << index):
            run(setter["address"], provider[index])
    if replaced:
        run(setters[replaced - 1]["address"], provider[5])
    if destroyed:
        # Reproduce destruction notification by executing the native callback.
        offset = receiver + OFFSETS[destroyed - 1]
        ptr = get(offset)
        run(changed["address"], ptr, 5)
        assert get(offset) == 0 and death == [provider.index(ptr) + 1]
        registered.remove(death[0])
    if borrowed:
        assert not registered
        # Independent host borrow compatibility has no native setter analogue.
        assert all(get(receiver + offset) == 0 for offset in OFFSETS)
    bitmap = provider[6]
    put(bitmap + 0x34, 3)
    if primary:
        put(receiver + 0x58, bitmap)
    running_destructor = True
    run(target["address"])
    assert live == (not bool(deallocator)) and events[-1][0] == ("base" if live else "delete")
    assert all(event[0] != "remove" for event in events[events.index(["base", primary]):])
    bitmap_count = get(bitmap + 0x34)
    assert bitmap_count == 3 - primary
    return dict(inputs=list(case), receiver_released=not live, events=events,
                setter_events=setup, destroyed_provider=death, trace=trace, writes=writes,
                bitmap_refcount=bitmap_count)
