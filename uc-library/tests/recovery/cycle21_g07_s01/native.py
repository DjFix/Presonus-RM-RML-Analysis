"""Execute the exact original Solo application bodies and compiler comparator."""
import hashlib
import json
import struct
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_ARM, Uc
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP

ROOT = Path("/home/rs/projects/opencs/ai-line-analysis")
PACKETS = ROOT / "temp/recovery-work/reconstruction10x10-20261121/packeting"
READ_MAP = PACKETS / "READ_INPUTS-post32-next-batch02-cycle21_g07-post32-next39-scoped03-dispatch02.json"
ELF_SHA = "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0"
ORIGINALS = {
    "cycle21_g07_s01": ("_ZN8Presonus7Surface17SoloPageComponent10clearSolosEv", 0x95B18, 188,
                        "5527e7b39c1a36cf26a282e08ab2a1714acb996750ced5143b7dcad5a6f9cb6e"),
    "cycle21_g07_s02": ("_ZN8Presonus7Surface17SoloPageComponent12paramChangedEPN4Core8Portable9ParameterEi", 0x95BDC, 136,
                        "ab2667f464bf1ca31d5c75b1a0e0d6ea00619f242b7f144451aea5a63ca71ca9"),
}
S01, S02 = ORIGINALS.values()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def execute(segments, mode, message, tag, bits):
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    low = min(a for a, n, b in segments) & ~4095
    high = (max(a + n for a, n, b in segments) + 4095) & ~4095
    uc.mem_map(low, high - low)
    for a, n, b in segments:
        uc.mem_write(a, b)
    base = 0x3000000
    uc.mem_map(base, 0x10000)
    page, mixer, line, aux, channel1, channel2, channel3, param1, param3, button, info, vec, halt = (
        base + i * 256 for i in range(13))
    put = lambda address, word: uc.mem_write(address, struct.pack("<I", word))
    word = lambda address: struct.unpack("<I", uc.mem_read(address, 4))[0]
    if mode != 0:
        put(page + 0xCC, mixer)
    put(mixer, 0x19A310)
    put(line + 0x58, vec)
    put(line + 0x5C, 2)
    put(vec, channel1)
    put(vec + 4, channel2)
    put(aux + 0x58, vec + 8)
    put(aux + 0x5C, 1)
    put(vec + 8, channel3)
    for parameter in (param1, param3, button):
        put(parameter, 0x2051B0)
    put(button + 0xC, info)
    put(info + 4, tag)
    trace = []
    comparator = set()

    def hook(machine, address, size, _):
        r0 = machine.reg_read(UC_ARM_REG_R0)
        r1 = machine.reg_read(UC_ARM_REG_R1)
        ret = machine.reg_read(UC_ARM_REG_LR)
        if address == halt:
            machine.emu_stop()
            return
        if S01[1] <= address < S01[1] + S01[2] or S02[1] <= address < S02[1] + S02[2]:
            if address == S01[1]:
                trace.append(["clear", 0])
            return
        if address == 0x5D72C:
            assert r0 == mixer and ret == 0x95B60 and r1 in (0, 4)
            trace.append(["group", r1])
            result = {0: line, 4: aux}[r1] if mode == 2 else 0
        elif address == 0x11ACF0:
            assert ret == 0x95B90 and r1 == 14
            trace.append(["lookup", {channel1: 1, channel2: 2, channel3: 3}[r0]])
            result = {channel1: param1, channel2: 0, channel3: param3}[r0]
        elif address == 0x11E5D4:
            label = {button: "button", param1: "line", param3: "aux"}[r0]
            assert (ret, r1) == ((0x95C24, 0) if r0 == button else (0x95BA8, 1))
            trace.append([label, r1])
            result = 0
        elif address == 0x11E48C:
            assert r0 == button and ret == 0x95C48
            trace.append(["value", bits])
            result = bits
        elif 0x1876D0 <= address < 0x1877F8:
            comparator.add(address)
            return
        else:
            raise AssertionError(f"Unexpected hook {address:#x}")
        machine.reg_write(UC_ARM_REG_R0, result)
        machine.reg_write(UC_ARM_REG_PC, ret)

    assert word(0x19A330) == 0x5D72C
    assert (word(0x2051F4), word(0x20520C)) == (0x11E48C, 0x11E5D4)
    uc.reg_write(UC_ARM_REG_R0, page)
    uc.reg_write(UC_ARM_REG_R1, button)
    uc.reg_write(UC_ARM_REG_R2, message or 0)
    uc.reg_write(UC_ARM_REG_SP, base + 0x8000)
    uc.reg_write(UC_ARM_REG_LR, halt)
    uc.hook_add(UC_HOOK_CODE, hook)
    uc.emu_start(S01[1] if message is None else S02[1], halt + 4, count=2000)
    assert uc.reg_read(UC_ARM_REG_PC) == halt
    return dict(mode=mode, message=message, tag=tag, value_bits=bits, trace=trace,
                comparator_instructions=len(comparator))


def observe(task):
    mapping = json.loads(READ_MAP.read_text())["rootfs/CS18_v13840/home/root/surface"]
    path = Path(mapping["frozen_read_path"])
    data = path.read_bytes()
    assert sha(data) == mapping["sha256"] == ELF_SHA
    exact = {}
    with path.open("rb") as stream:
        elf = ELFFile(stream)
        symtab = elf.get_section_by_name(".symtab")
        for identity, addr, size, digest in ORIGINALS.values():
            (symbol,) = symtab.get_symbol_by_name(identity)
            assert symbol["st_value"] == addr and symbol["st_size"] == size
            section = elf.get_section(symbol["st_shndx"])
            offset = section["sh_offset"] + addr - section["sh_addr"]
            assert sha(data[offset:offset + size]) == digest
            exact[identity] = dict(mangled=identity, address=addr, size=size,
                                   section=section.name, file_offset=offset, range_sha256=digest)
        segments = [(s["p_vaddr"], s["p_memsz"], s.data())
                    for s in elf.iter_segments() if s["p_type"] == "PT_LOAD"]
    identity = ORIGINALS[task][0]
    tests = ([(mode, None, 0, 0) for mode in range(3)] if identity == S01[0] else
             [(2, msg, tag, 0x3F000000) for msg in (1, 2, 3) for tag in (99, 100)] +
             [(2, 2, 100, bits) for bits in (0, 0x80000000, 0xBF000000, 0x7FC00000)])
    return dict(task=task, elf_sha256=ELF_SHA, **exact[identity],
                co_owned_range=exact[S01[0]] if identity == S02[0] else None,
                dispatch_slots={"mixer_getChannelGroup": [0x19A330, 0x5D72C],
                                "numeric_getValue": [0x2051F4, 0x11E48C],
                                "numeric_resetValue": [0x20520C, 0x11E5D4]},
                cases=[execute(segments, *case) for case in tests],
                oracle="Exact original ARM application ranges and ARM __aeabi_fcmpgt execute. "
                       "Provider boundary results are controlled; linked native vtable words and "
                       "actual receiver/call ordering are checked. Host uses real CCL providers.")


if __name__ == "__main__":
    print(json.dumps(observe(Path(__file__).parent.name), indent=2))
