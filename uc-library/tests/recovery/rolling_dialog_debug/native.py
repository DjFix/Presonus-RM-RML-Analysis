"""Execute original app bodies with the pinned source-provider boundary modeled."""
import argparse
import hashlib
import io
import json
import struct
from pathlib import Path

import unicorn
from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn import UC_MODE_ARM, Uc
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0
from unicorn.arm_const import UC_ARM_REG_R1, UC_ARM_REG_SP

PREFIX = "_ZN8Presonus17IDAWDialogHandler10DialogMenu"
VECTOR = "_ZN4Core6VectorIPN8Presonus17IDAWDialogHandler10DialogMenuEE"
DEBUG = "5debugEv"
OBJECT = 0x600000
STACK = 0x701000
RETURN = 0x500000
ELFS = [
    ("RM/RML mixer 13731", "server", "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07",
     [0x1331C, 0x134CC, 0x1368C, 0x137BC, 0x1384C]),
    ("CS18AI surface 13840", "client", "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0",
     [0x534B8, 0x53668, 0x53828, 0x53958, 0x539E8]),
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def observe(path, identity):
    firmware, role, elf_hash, addresses = identity
    elf_bytes = path.read_bytes()
    assert digest(elf_bytes) == elf_hash
    elf = ELFFile(io.BytesIO(elf_bytes))
    symbols = {s.name: s for s in elf.get_section_by_name(".symtab").iter_symbols()}
    ranges = {}

    def locate(name):
        symbol = symbols[name]
        section_index = symbol["st_shndx"]
        section = elf.get_section(section_index)
        address, size = symbol["st_value"], symbol["st_size"]
        relative = address - section["sh_addr"]
        assert section.name == ".text" and 0 <= relative <= section["sh_size"] - size
        offset = section["sh_offset"] + relative
        return address, size, section_index, offset

    vm = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    text = elf.get_section_by_name(".text")
    text_start = text["sh_addr"] & ~0xFFF
    text_end = (text["sh_addr"] + text["sh_size"] + 0xFFF) & ~0xFFF
    vm.mem_map(text_start, text_end - text_start)
    vm.mem_map(OBJECT, 0x1000)
    vm.mem_map(STACK - 0x1000, 0x1000)

    for suffix, address, size in zip(
        [DEBUG, "C1Ev", "C2Ev", "D1Ev", "D2Ev"], addresses, [16, 88, 88, 144, 144]
    ):
        name = PREFIX + suffix
        actual_address, actual_size, section, offset = locate(name)
        assert (actual_address, actual_size, section) == (address, size, 12)
        body = elf_bytes[offset:offset + size]
        sha = digest(body)
        if suffix == DEBUG:
            assert sha == "60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad"
        vm.mem_write(address, body)
        ranges[suffix] = dict(mangled=name, address=address, size=size, section=section,
                              file_offset=offset, range_sha256=sha)
    resize = locate(VECTOR + "6resizeEi")[0]
    destroy = locate(VECTOR + "D1Ev")[0]
    trace = []
    debug_access = []

    def words():
        return struct.unpack("<9I", vm.mem_read(OBJECT, 36))

    def code_hook(uc, address, _size, _data):
        if address in (resize, destroy):
            assert uc.reg_read(UC_ARM_REG_R0) == OBJECT + 0x10
            elements, count, capacity, delta = words()[5:9]
            assert (elements, count, capacity, delta) == (0, 0, 0, 5)
            if address == resize:
                assert uc.reg_read(UC_ARM_REG_R1) == 0
                trace.append("Vector::resize(0), count=0, capacity=0, storage=null")
                uc.reg_write(UC_ARM_REG_R0, 1)
            else:
                trace.append("Vector::~Vector(), count=0, capacity=0, storage=null")
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
        else:
            assert any(row["address"] <= address < row["address"] + row["size"]
                       for row in ranges.values()), hex(address)

    vm.hook_add(UC_HOOK_CODE, code_hook)

    def execute(suffix):
        vm.reg_write(UC_ARM_REG_R0, OBJECT)
        vm.reg_write(UC_ARM_REG_SP, STACK)
        vm.reg_write(UC_ARM_REG_LR, RETURN)
        vm.emu_start(ranges[suffix]["address"], RETURN, count=200)
        assert vm.reg_read(UC_ARM_REG_PC) == RETURN and vm.reg_read(UC_ARM_REG_SP) == STACK

    def access(_vm, _kind, address, size, _value, _data):
        debug_access.append((address, size))

    cases = []
    for ctor, dtor in (("C1Ev", "D1Ev"), ("C2Ev", "D2Ev")):
        for prefill in (0x55, 0xAA):
            vm.mem_write(OBJECT, bytes([prefill]) * 64)
            trace.clear()
            execute(ctor)
            assert len(trace) == 1 and trace[0].startswith("Vector::resize(0)")
            state = words()
            assert state[:4] == (0, 0, 0, 0) and state[5:9] == (0, 0, 0, 5)
            before = bytes(vm.mem_read(OBJECT, 64))
            debug_access.clear()
            hook = vm.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, access)
            for _ in range(3):
                execute(DEBUG)
            vm.hook_del(hook)
            assert debug_access and all(STACK - 16 <= address <= STACK - size
                                        for address, size in debug_access)
            assert bytes(vm.mem_read(OBJECT, 64)) == before and len(trace) == 1
            execute(dtor)
            assert len(trace) == 2 and trace[1].startswith("Vector::~Vector()")
            cases.append(dict(constructor=ctor, destructor=dtor, prefill=prefill,
                              initialized_words=list(state), debug_calls=3,
                              debug_stack_only_accesses=len(debug_access),
                              debug_receiver_unchanged=True, lifecycle_calls=list(trace)))
    return dict(elf_sha256=elf_hash, firmware=firmware, role=role, debug_range=ranges[DEBUG],
                lifecycle_ranges=[row for key, row in ranges.items() if key != DEBUG],
                provider_targets=dict(resize=resize, destroy=destroy), cases=cases)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mixer", type=Path, required=True)
    parser.add_argument("--surface", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    result = [observe(path, identity) for path, identity in zip((args.mixer, args.surface), ELFS)]
    rendered = json.dumps(result, indent=2) + "\n"
    if args.record:
        args.fixtures.write_text(rendered)
    else:
        assert args.fixtures.read_text() == rendered
    print(f"{sum(len(row['cases']) for row in result)} native lifecycle sequences passed (Unicorn {unicorn.__version__})")


if __name__ == "__main__":
    main()
