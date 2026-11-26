"""Execute role-specific D0 through relocated firmware libc and libstdc++."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UcError, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_INTR, UC_HOOK_MEM_WRITE, __version__
from unicorn.arm_const import (
    UC_ARM_REG_CPSR, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0,
    UC_ARM_REG_R7, UC_ARM_REG_SP,
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


class Image:
    def __init__(self, path, sha256, base=0):
        self.data = path.read_bytes()
        assert digest(self.data) == sha256, path
        self.elf = ELFFile(io.BytesIO(self.data))
        self.base = base

    def symbol(self, name, section=".dynsym"):
        matches = self.elf.get_section_by_name(section).get_symbol_by_name(name)
        return next(symbol for symbol in matches if symbol["st_shndx"] != "SHN_UNDEF")

    def address(self, name):
        return self.base + self.symbol(name)["st_value"]

    def load(self, arm):
        segments = [s for s in self.elf.iter_segments() if s["p_type"] == "PT_LOAD"]
        start = self.base + min(s["p_vaddr"] & ~4095 for s in segments)
        end = self.base + max((s["p_vaddr"] + s["p_memsz"] + 4095) & ~4095 for s in segments)
        arm.mem_map(start, end - start)
        for segment in segments:
            arm.mem_write(self.base + segment["p_vaddr"], segment.data())

    def relocate(self, arm, providers):
        for section in self.elf.iter_sections():
            if section.name not in (".rel.dyn", ".rel.plt"):
                continue
            symbols = self.elf.get_section(section["sh_link"])
            for rel in section.iter_relocations():
                address = self.base + rel["r_offset"]
                kind = rel["r_info_type"]
                if kind == 23:  # R_ARM_RELATIVE
                    put(arm, address, self.base + word(arm, address))
                elif kind in (2, 21, 22):  # ABS32, GLOB_DAT, JUMP_SLOT
                    symbol = symbols.get_symbol(rel["r_info_sym"])
                    value = providers.get(symbol.name)
                    if value is None and symbol["st_shndx"] != "SHN_UNDEF":
                        value = self.base + symbol["st_value"]
                    if value is not None:
                        put(arm, address, value + (word(arm, address) if kind == 2 else 0))
                    else:
                        put(arm, address, 0)


def word(arm, address):
    return struct.unpack("<I", arm.mem_read(address, 4))[0]


def put(arm, address, value):
    arm.mem_write(address, struct.pack("<I", value))


def call(arm, entry, argument):
    arm.reg_write(UC_ARM_REG_SP, 0x7100fff0)
    arm.reg_write(UC_ARM_REG_LR, 0x71010000)
    arm.reg_write(UC_ARM_REG_R0, argument)
    try:
        arm.emu_start(entry, 0x71010000, count=500000)
    except UcError as error:
        raise RuntimeError(f"{entry:#x}: PC={arm.reg_read(UC_ARM_REG_PC):#x} LR={arm.reg_read(UC_ARM_REG_LR):#x} {error}") from error
    assert arm.reg_read(UC_ARM_REG_PC) == 0x71010000, hex(entry)
    return arm.reg_read(UC_ARM_REG_R0)


def verified_body(app, arm, original):
    address = original["address"]
    symbol = app.symbol(original["mangled"], ".symtab")
    section = app.elf.get_section(original["section"])
    offset = section["sh_offset"] + address - section["sh_addr"]
    assert symbol["st_value"] == address and symbol["st_size"] == original["size"]
    assert symbol["st_shndx"] == original["section"] and section.name == original["section_name"]
    assert 0 <= address - section["sh_addr"] <= section["sh_size"] - original["size"]
    assert offset == original["file_offset"]
    body = app.data[offset:offset + original["size"]]
    assert digest(body) == original["range_sha256"]
    assert body.hex() == original["range_hex"]
    assert bytes(arm.mem_read(address, len(body))) == body
    return body


def read_string(arm, address):
    string = bytearray()
    for offset in range(128):
        byte, = arm.mem_read(address + offset, 1)
        if not byte:
            return string.decode("ascii")
        string.append(byte)
    raise AssertionError("unterminated string")


def run_role(root, original, companion, allocator, heap_base):
    app = Image(root / original["elf_path"], original["elf"])
    cxx = Image(root / allocator["operator_delete"]["path"], allocator["operator_delete"]["sha256"], 0x20000000)
    libc = Image(root / allocator["free"]["path"], allocator["free"]["sha256"], 0x30000000)
    loader_path = Path(allocator["free"]["path"]).with_name("ld-2.9.so")
    loader = Image(root / loader_path, "2f9c215d1ff20fd3ac9417eacfcd288a0bbf5cedb14117b7a5f92f69a17c3b67", 0x40000000)
    arm = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    arm.reg_write(UC_ARM_REG_CPSR, 0x10)
    for image in (app, cxx, libc, loader):
        image.load(arm)
    arm.mem_map(0x71000000, 0x10000)
    arm.mem_map(heap_base, 0x400000)
    heap_end = heap_base
    syscalls = []

    def syscall(uc, interrupt, _):
        nonlocal heap_end
        nr = uc.reg_read(UC_ARM_REG_R7)
        argument = uc.reg_read(UC_ARM_REG_R0)
        syscalls.append(nr)
        if nr != 45 or not (argument == 0 or heap_base <= argument < heap_base + 0x400000):
            raise RuntimeError(f"unexpected syscall {nr} interrupt {interrupt} argument {argument:#x}")
        if argument:
            heap_end = argument
        uc.reg_write(UC_ARM_REG_R0, heap_end)

    arm.hook_add(UC_HOOK_INTR, syscall)
    loader.relocate(arm, {})
    # Single-thread loader callbacks used by dladdr during allocator initialization.
    arm.mem_map(0x72000000, 0x1000)
    put(arm, 0x72000000, 0xe12fff1e)  # bx lr
    for offset in (0x548, 0x54c):
        put(arm, loader.address("_rtld_global") + offset, 0x72000000)
    # Linux ARM kuser_get_tls returns the modeled thread pointer.
    arm.mem_map(0xffff0000, 0x1000)
    arm.mem_map(0x73000000, 0x1000)
    put(arm, 0xffff0fe0, 0xe59f0000)  # ldr r0, [pc]
    put(arm, 0xffff0fe4, 0xe12fff1e)  # bx lr
    put(arm, 0xffff0fe8, 0x73000800)
    # ARM kuser_cmpxchg contract, serialized by the single-thread emulator.
    for index, instruction in enumerate((0xe5923000, 0xe0533000, 0x05821000, 0xe2730000, 0xe12fff1e)):
        put(arm, 0xffff0fc0 + 4 * index, instruction)
    libc.relocate(arm, {name: loader.address(name) for name in ("_rtld_global", "_rtld_global_ro", "__libc_enable_secure", "_dl_argv", "__tls_get_addr")})
    cxx.relocate(arm, {"free": libc.address("free")})
    app.relocate(arm, {"_ZdlPv": cxx.address("_ZdlPv")})
    body = verified_body(app, arm, original)
    complete_body = verified_body(app, arm, companion)
    address = original["address"]
    d1 = companion["address"]
    malloc = libc.address("malloc")
    cxx_delete = cxx.address("_ZdlPv")
    free = libc.address("free")
    delete_delta = struct.unpack_from("<I", body, 28)[0]
    assert delete_delta >> 24 == 0xeb
    signed_words = (delete_delta & 0xffffff) - (0x1000000 if delete_delta & 0x800000 else 0)
    plt_delete = address + 28 + 8 + signed_words * 4
    imported, = app.elf.get_section_by_name(".dynsym").get_symbol_by_name("_ZdlPv")
    assert imported["st_shndx"] == "SHN_UNDEF" and imported["st_value"] == plt_delete
    vptr = struct.unpack("<I", body[-4:])[0]
    assert struct.unpack("<I", complete_body[-4:])[0] == vptr
    vtable = app.symbol(original["mangled"].replace("_ZN", "_ZTVN").replace("D0Ev", "E"), ".symtab")
    complete_vptr = vtable["st_value"] + 8
    assert word(arm, complete_vptr) == d1
    assert word(arm, complete_vptr + 4) == address
    assert vptr == app.symbol("_ZTVN4Core9FormatterE", ".symtab")["st_value"] + 8
    initializer = app.symbol("_ZN8Presonus5Mixer24XmenFormatterInitializer8addClassINS0_15FxTypeFormatterEEEvv", ".symtab")
    name = word(arm, initializer["st_value"] + 120)
    assert read_string(arm, name) == "fxtype"
    events = []
    def observe(uc, pc, _size, _):
        pointer = uc.reg_read(UC_ARM_REG_R0)
        assert word(uc, pointer + 4) == name
        events.append((pc, pointer, word(uc, pointer)))

    for point in (plt_delete, cxx_delete, free):
        arm.hook_add(UC_HOOK_CODE, observe, begin=point, end=point)

    object_symbol = app.symbol("_ZZN8Presonus5Mixer24XmenFormatterInitializer8addClassINS0_15FxTypeFormatterEEEvvE12theFormatter", ".symtab")
    assert object_symbol["st_size"] == 12
    pointer = call(arm, malloc, 12)
    guard = call(arm, malloc, 12)
    assert heap_base <= pointer < guard < heap_end
    # Seed the complete vptr, name and prefix observed in the original initializer.
    for receiver in (pointer, guard):
        put(arm, receiver, complete_vptr)
        put(arm, receiver + 4, name)
        put(arm, receiver + 8, 0xa5a5a554)
    lifetime_writes = []

    def write(_arm, _access, location, size, value, _data):
        lifetime_writes.append([location, size, value])

    for receiver in (pointer, guard):
        arm.hook_add(UC_HOOK_MEM_WRITE, write, begin=receiver, end=receiver + 11)
    assert call(arm, word(arm, word(arm, guard)), guard) == guard
    assert lifetime_writes == [[guard, 4, vptr]]
    assert word(arm, guard + 4) == name and word(arm, guard + 8) == 0xa5a5a554
    assert word(arm, guard) == vptr
    complete_events = list(events)
    assert not complete_events
    spare = call(arm, malloc, 12)
    assert spare not in (pointer, guard)
    before = word(arm, pointer)
    assert before == complete_vptr
    assert call(arm, word(arm, before + 4), pointer) == pointer
    assert events == [(p, pointer, vptr) for p in (plt_delete, cxx_delete, free)], events
    assert lifetime_writes[1] == [pointer, 4, vptr]
    reused = call(arm, malloc, 12)
    assert reused == pointer, (pointer, reused)
    return {
        "role": original["role"], "original": original, "allocator": allocator,
        "complete_original": companion, "complete_delete_entries": complete_events, "unicorn_version": __version__, "malloc": malloc, "events": [list(event) for event in events],
        "lifetime_vptr_writes": lifetime_writes[:2],
        "loader": {"path": str(loader_path), "sha256": digest(loader.data)},
        "complete_vptr_before_d0": before, "borrowed_name": name, "name": "fxtype",
        "receiver": pointer, "guard": guard, "allocation_after_d1": spare,
        "allocation_after_d0": reused, "vptr": vptr, "syscalls": syscalls,
    }


ISSUED = Path("temp/recovery-work/sqlite-issued/packet")
D0 = "sqlite06_reverb_fxtype_deleting_destroy"
D1 = "sqlite06_reverb_fxtype_complete_destroy"


def originals(task):
    return [row["original"] for row in json.loads((ISSUED / task / "CONTEXT.json").read_text())["originals"]]


def firmware_root(original):
    # The assigned checkout points directly to the captured app ELF. Its
    # enclosing checkout also contains the captured sysroot.
    return Path(original["elf_path"]).resolve().parents[4]


def generate():
    d1 = {row["elf"]: row for row in originals(D1)}
    results = []
    for index, original in enumerate(originals(D0)):
        rootfs = Path(original["elf_path"]).parents[2]
        allocator = {
            "operator_delete": {
                "path": str(rootfs / "usr/lib/libstdc++.so.6.0.10"),
                "sha256": "c523a78aa347276b59ae9b373a15a79fa623b84574a67739475aa2ea44a66cf3",
            },
            "free": {
                "path": str(rootfs / "lib/libc-2.9.so"),
                "sha256": "0cc1cb572b2a2cc52f51adf82acd1be7eb5e08f96049b04e280ebad594636efb",
            },
        }
        results.append(run_role(firmware_root(original), original, d1[original["elf"]],
                                allocator, 0x50000000 + index * 0x01000000))
    return results


def cli(produce):
    parser = argparse.ArgumentParser(description=__doc__)
    output = parser.add_mutually_exclusive_group(required=True)
    output.add_argument("--out", type=Path)
    output.add_argument("--verify", type=Path)
    args = parser.parse_args()
    result = produce()
    if args.out:
        args.out.write_text(json.dumps(result, indent=2) + "\n")
    else:
        assert result == json.loads(args.verify.read_text())
    print(f"Original ARM replay matched {len(result)} firmware roles")


if __name__ == "__main__":
    cli(generate)
