"""Execute original recursive MainLCD destruction notifications."""
import hashlib
import json
import struct
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_ARM, Uc
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP

ROOT = Path("/home/rs/projects/opencs/ai-line-analysis")
RUN = ROOT / "temp/recovery-work/reconstruction10x10-20261121/packeting"
READ_MAP = RUN / "READ_INPUTS-post32-next-batch02-cycle21_g07-post32-next39-scoped01-dispatch02.json"
ELF_SHA = "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0"
MANGLED = "_ZN8Presonus16MainLCDComponent16prenotifyDestroyEPN4Core8Portable13ContainerViewE"
START, SIZE = 0x73658, 156
RANGE_SHA = "f1bcd27c56bbf74ef36bb7256b6a16dde07d68ecc3176596b5e8ffcd085e7ac8"


def sha(value):
    return hashlib.sha256(value).hexdigest()


def execute(segments, nested, owner_present):
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    start = min(a for a, n, b in segments) & ~4095
    end = (max(a + n for a, n, b in segments) + 4095) & ~4095
    uc.mem_map(start, end - start)
    for a, _, b in segments:
        uc.mem_write(a, b)
    base = 0x3000000
    uc.mem_map(base, 0x10000)
    root, leaf, branch, tip, owner, view_table, owner_table, vector, callbacks = [base + i * 256 for i in range(9)]
    put = lambda a, v: uc.mem_write(a, struct.pack("<I", v))
    get = lambda a: struct.unpack("<I", uc.mem_read(a, 4))[0]
    views = {root: "root", leaf: "leaf", branch: "branch", tip: "tip"}
    for view in views:
        put(view, 0x204438 if view == leaf else 0x2043A0)
    put(root + 0x44, owner if owner_present else 0)
    if nested:
        put(branch + 0x44, owner)
        put(tip + 0x44, owner)
        put(root + 0x48, vector)
        put(root + 0x4C, 2)
        put(vector, leaf)
        put(vector + 4, branch)
        put(branch + 0x48, vector + 8)
        put(branch + 0x4C, 1)
        put(vector + 8, tip)
    put(owner, owner_table)
    put(owner_table, callbacks)
    stop = callbacks + 8
    notifications, visits, container_queries = [], [], []

    def hook(machine, address, size, _):
        receiver = machine.reg_read(UC_ARM_REG_R0)
        ret = machine.reg_read(UC_ARM_REG_LR)
        if address == stop:
            machine.emu_stop()
        elif address == START:
            if visits:
                assert ret == 0x736E0
            visits.append(views[receiver])
        elif address == callbacks:
            view = machine.reg_read(UC_ARM_REG_R1)
            assert receiver == owner and get(view + 0x44) == owner
            notifications.append(views[view])
            machine.reg_write(UC_ARM_REG_PC, ret)
        elif address in (0x10E8E4, 0x10EC8C):
            assert (address == 0x10E8E4) == (receiver == leaf)
            assert ret == 0x736D4
            container_queries.append(views[receiver])
            machine.reg_write(UC_ARM_REG_R0, 0 if address == 0x10E8E4 else receiver)
            machine.reg_write(UC_ARM_REG_PC, ret)
        elif not START <= address < START + SIZE:
            raise AssertionError(f"Unexpected original destination {address:#x}")

    uc.reg_write(UC_ARM_REG_R0, root)
    uc.reg_write(UC_ARM_REG_R1, 0xDEADBEEF)  # unused at entry: this is a static member
    uc.reg_write(UC_ARM_REG_SP, base + 0x8000)
    uc.reg_write(UC_ARM_REG_LR, stop)
    uc.hook_add(UC_HOOK_CODE, hook)
    uc.emu_start(START, stop + 4, count=1000)
    assert uc.reg_read(UC_ARM_REG_PC) == stop
    return dict(nested=nested, owner_present=owner_present, notifications=notifications,
                visits=visits, container_queries=container_queries,
                owners_cleared=all(get(view + 0x44) == 0 for view in views))


def observe():
    mapping = json.loads(READ_MAP.read_text())["rootfs/CS18_v13840/home/root/surface"]
    path = Path(mapping["frozen_read_path"])
    file_bytes = path.read_bytes()
    assert sha(file_bytes) == mapping["sha256"] == ELF_SHA
    with path.open("rb") as fp:
        elf = ELFFile(fp)
        matches = elf.get_section_by_name(".symtab").get_symbol_by_name(MANGLED)
        assert len(matches) == 1
        symbol = matches[0]
        assert symbol["st_value"] == START and symbol["st_size"] == SIZE
        section = elf.get_section(symbol["st_shndx"])
        offset = section["sh_offset"] + START - section["sh_addr"]
        assert sha(file_bytes[offset:offset + SIZE]) == RANGE_SHA
        segments = [(s["p_vaddr"], s["p_memsz"], s.data())
                    for s in elf.iter_segments() if s["p_type"] == "PT_LOAD"]
    return dict(task="cycle21_g07_s08", elf_sha256=ELF_SHA, mangled=MANGLED, address=START, size=SIZE,
                section=section.name, file_offset=offset, range_sha256=RANGE_SHA,
                view_virtual_bindings={"View::asContainer": [0x204448, 0x10E8E4],
                                       "ContainerView::asContainer": [0x2043B0, 0x10EC8C]},
                cases=[execute(segments, nested, owner) for nested, owner in
                       ((False, False), (False, True), (True, False), (True, True))],
                oracle="Original ARM target executes each recursive entry and actual owner clearing "
                       "stores. Explicit vtable boundaries model get-container and owner notification.")


if __name__ == "__main__":
    print(json.dumps(observe(), indent=2))
