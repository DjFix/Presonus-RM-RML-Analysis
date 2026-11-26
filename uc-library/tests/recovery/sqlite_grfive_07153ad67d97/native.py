"""Observe the hash-verified GRMeterMaid entries with the ARM interpreter."""
import ctypes
import hashlib
import json
from pathlib import Path
import struct
import sys

from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc, UcError, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0 as R0, UC_ARM_REG_R1 as R1, UC_ARM_REG_LR as LR
from unicorn.arm_const import UC_ARM_REG_SP as SP, UC_ARM_REG_PC as PC

OBJECT, PARAM, STACK, STOP = (0x22000000, 0x23000000, 0x24000000, 0x25000000)
MAID = "_ZN8Presonus9MeterMaidC2Ev"
BALLISTICS = "_ZN8Presonus15MeterBallistics"
DECAY_TABLE = BALLISTICS + "15MeterDecayTableC1EPKf"
DECAY = "_ZNK8Presonus15MeterBallistics13getDecayDeltaEv"
PEAK_DECAY = "_ZNK8Presonus15MeterBallistics17getPeakDecayDeltaEv"
HELPERS = ("__aeabi_fcmpgt", "__aeabi_fcmplt", "__aeabi_fcmpge", "__aeabi_fcmple",
           "__aeabi_fsub", "__aeabi_fmul", "__aeabi_fdiv", "__aeabi_cfcmple",
           "__aeabi_cfcmpeq", "__aeabi_cfrcmple", "__cmpsf2", "__ltsf2")
POW = ctypes.CDLL("libm.so.6").powf
POW.argtypes = [ctypes.c_float, ctypes.c_float]
POW.restype = ctypes.c_float


def digest(data):
    return hashlib.sha256(data).hexdigest()


def words(data):
    return list(struct.unpack(f"<{len(data)//4}I", data))


def bits(number):
    return words(struct.pack("<f", number))[0]


def float32(word):
    return struct.unpack("<f", struct.pack("<I", word))[0]


def observe(target):
    with Path(target["elf_path"]).open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == target["elf"]
        stream.seek(0)
        elf = ELFFile(stream)
        symbols = elf.get_section_by_name(".symtab")
        plt = elf.get_section_by_name(".plt")
        relocations = elf.get_section_by_name(".rel.plt")
        dynsym = elf.get_section(relocations["sh_link"])
        imports = {plt["sh_addr"] + 20 + 12 * index: dynsym.get_symbol(row["r_info_sym"]).name
                   for index, row in enumerate(relocations.iter_relocations())
                   if row["r_info_type"] == 22}
        segments = [(s["p_vaddr"], s["p_memsz"], s.data())
                    for s in elf.iter_segments() if s["p_type"] == "PT_LOAD"]

        def span(name):
            symbol, = symbols.get_symbol_by_name(name)
            section_index = symbol["st_shndx"]
            section = elf.get_section(section_index)
            begin, size = symbol["st_value"], symbol["st_size"]
            offset = begin - section["sh_addr"]
            assert 0 <= offset <= section["sh_size"] - size
            data = section.data()[offset:offset+size]
            return dict(mangled=name, address=begin, size=size, section=section_index,
                        section_name=section.name, file_offset=section["sh_offset"] + offset,
                        range_sha256=digest(data)), data

        extent, body = span(target["mangled"])
        assert all(target[key] == value for key, value in extent.items())
        assert target["range_hex"] == body.hex()
        vtable, _ = span("_ZTVN8Presonus11GRMeterMaidE")
        base_vtable, _ = span("_ZTVN8Presonus15MeterBallisticsE")
        numeric_vtable, _ = span("_ZTVN4Core8Portable12NumericParamE")
        assert not symbols.get_symbol_by_name("_ZN8Presonus11GRMeterMaidD2Ev")
        c1, _ = span("_ZN8Presonus11GRMeterMaidC1Ev")
        c2, _ = span("_ZN8Presonus11GRMeterMaidC2Ev")
        assert c1["address"] != c2["address"]
        helpers = [span(name)[0] for name in HELPERS if symbols.get_symbol_by_name(name)]
        providers = {name: span(name)[0] for name in
                     (MAID, BALLISTICS + "C2Ev", DECAY_TABLE,
                      DECAY, PEAK_DECAY)}
        base_body = span(BALLISTICS + "C2Ev")[1]
        _, _, guard, table, defaults = words(base_body[-20:])

    cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    low = min(address for address, _, _ in segments) & ~4095
    high = max(address + size for address, size, _ in segments)
    cpu.mem_map(low, (high-low+4095) & ~4095)
    for address, _, data in segments:
        cpu.mem_write(address, data)
    for address in (OBJECT, PARAM, STACK, STOP):
        cpu.mem_map(address, 4096)
    for row in (extent, c1, vtable, base_vtable, numeric_vtable, *providers.values(), *helpers):
        assert digest(bytes(cpu.mem_read(row["address"], row["size"]))) == row["range_sha256"]

    def word(address):
        return words(cpu.mem_read(address, 4))[0]

    def write(address, value):
        cpu.mem_write(address, struct.pack("<I", value))

    def get_state():
        return [cpu.mem_read(OBJECT+4, 1)[0], word(OBJECT+8), word(OBJECT+12),
                cpu.mem_read(OBJECT+16, 1)[0], *words(cpu.mem_read(OBJECT+20, 24))]

    assert words(cpu.mem_read(defaults, 24)) == [bits(v) for v in (-72, -45, -20, -6, -2, 0)]
    variant = target["mangled"][-4:-2]
    assert variant in ("C1", "C2", "D1", "D0")
    constructor = variant.startswith("C")
    expected_vptr = words(body[-4:])[0]
    assert expected_vptr == (vtable if constructor else base_vtable)["address"] + 8
    addresses = {r["address"]: r["mangled"] for r in (*providers.values(), extent, c1)}
    spans = [extent, c1, *providers.values(), *helpers]
    active = {}

    def on_instruction(machine, pc, _size, _data):
        if pc in addresses:
            active["entries"].append(addresses[pc])
        x, y = machine.reg_read(R0), machine.reg_read(R1)
        name = imports.get(pc)
        if name == "powf":
            machine.reg_write(R0, bits(POW(float32(x), float32(y))))
        elif name == "__cxa_guard_acquire":
            assert x == guard
            machine.reg_write(R0, int(not word(x) & 1))
        elif name == "__cxa_guard_release":
            assert x == guard
            write(guard, 1)
        elif name == "_ZdlPv":
            assert pc == active["delete_plt"] and x == OBJECT and word(x) == expected_vptr
            assert bytes(machine.mem_read(OBJECT+4, 92)) == active["before"][4:]
            machine.mem_unmap(x, 4096)
        else:
            assert any(r["address"] <= pc < r["address"] + r["size"] for r in spans), hex(pc)
            return
        active["imports"].append([name, pc, x, y if name == "powf" else None])
        machine.reg_write(PC, machine.reg_read(LR))

    def on_write(machine, _access, address, size, value, _data):
        if OBJECT <= address < OBJECT+96:
            active["writes"].append([machine.reg_read(PC), address-OBJECT, size, value])

    cpu.hook_add(UC_HOOK_CODE, on_instruction)
    cpu.hook_add(UC_HOOK_MEM_WRITE, on_write)

    def execute(address):
        for register, value in ((R0, OBJECT), (R1, 0), (LR, STOP), (SP, STACK+2048)):
            cpu.reg_write(register, value)
        cpu.emu_start(address, STOP, count=12000)
        assert (cpu.reg_read(PC), cpu.reg_read(SP)) == (STOP, STACK+2048)

    cases = []
    for index, seed in enumerate((0xa5, 0x5a)):
        cpu.mem_write(OBJECT, bytes([seed])*96)
        numeric_address = numeric_vtable["address"]+8
        write(PARAM, numeric_address)
        if not constructor:
            active.update(entries=[], imports=[], writes=[])
            execute(c1["address"])
            assert active["entries"][:3] == [c1["mangled"], MAID, BALLISTICS + "C2Ev"]
            assert word(OBJECT) == struct.unpack("<I", cpu.mem_read(c1["address"]+c1["size"]-4, 4))[0]
            assert word(OBJECT+0x2c) == 0
            construction = {key: active[key] for key in ("entries", "imports", "writes")}
            for slot in (0x30, 0x34, 0x38, 0x3c):
                write(OBJECT+slot, PARAM if index else 0)
        param_before = bytes(cpu.mem_read(PARAM, 64))
        del_plt, = [address for address, name in imports.items() if name == "_ZdlPv"]
        active.update(entries=[], imports=[], writes=[], delete_plt=del_plt,
                      before=bytes(cpu.mem_read(OBJECT, 96)))
        if constructor:
            assert bool(word(guard) & 1) == bool(index)
        execute(target["address"])
        entries = active["entries"].copy()
        if constructor:
            assert entries[:3] == [target["mangled"], MAID, BALLISTICS + "C2Ev"]
            assert (DECAY_TABLE in entries) == (index == 0)
            assert word(OBJECT) == expected_vptr
            slot_writes = [row for row in active["writes"] if row[1] == 0x2c]
            assert [row[3] for row in slot_writes] == [0, table, 0], slot_writes
            slots = words(cpu.mem_read(OBJECT+0x30, 16))
            assert slots == [0]*4
            state = get_state()
            table_words = words(cpu.mem_read(table, 40))
            constructor_observations = {key: active[key] for key in ("imports", "writes")}
            differential = {}
            for getter, slot in ((DECAY, 0x14), (PEAK_DECAY, 0x18)):
                write(OBJECT+slot, bits(0.5))
                active.update(entries=[], imports=[], writes=[])
                execute(providers[getter]["address"])
                without_table = cpu.reg_read(R0)
                write(OBJECT+0x2c, table)
                execute(providers[getter]["address"])
                with_table = cpu.reg_read(R0)
                assert with_table != without_table
                assert not active["imports"] and not active["writes"]
                differential[getter] = dict(input_binary32=bits(0.5),
                                            constructed_null=without_table,
                                            restored_table=with_table)
                write(OBJECT+0x2c, 0)
            active.update(constructor_observations)
            case = dict(state=state, table_words=table_words, slots=slots,
                        table_slot_writes=slot_writes, getter_differential=differential)
        else:
            assert entries == [target["mangled"]]
            assert len(active["writes"]) == 1 and active["writes"][0][1:] == [0, 4, expected_vptr]
            assert bytes(cpu.mem_read(PARAM, 64)) == param_before
            try:
                retained = bytes(cpu.mem_read(OBJECT, 96))
            except UcError as error:
                assert error.errno == unicorn.UC_ERR_READ_UNMAPPED
                retained = None
            assert (retained is None) == (variant == "D0")
            assert len(active["imports"]) == int(variant == "D0")
            if retained is not None:
                assert retained[4:] == active["before"][4:]
            else:
                cpu.mem_map(OBJECT, 4096)
            case = dict(deleted=retained is None, bound=bool(index), borrowed_unmodified=True,
                        construction=construction)
        cases.append(dict(seed=seed, entries=entries, imports=active["imports"],
                          writes=active["writes"], **case))
    return dict(target=target, providers=providers, helpers=helpers, vtable=vtable,
                base_vtable=base_vtable, numeric_vtable=numeric_vtable,
                retained_c1=c1, constructor_entries_distinct=True,
                cases=cases)


if __name__ == "__main__":
    packet = json.loads(Path(sys.argv[1]).read_text())
    print(json.dumps(dict(engine=f"Unicorn {unicorn.__version__}",
                          originals=[observe(row["original"]) for row in packet["originals"]]),
                     indent=2))
