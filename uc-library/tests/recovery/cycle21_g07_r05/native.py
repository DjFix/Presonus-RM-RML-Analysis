"""Execute original outer D0, original Audio D2 and original Dsp D2."""
import hashlib
import json
import struct
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_ARM, Uc, UcError
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_SP

ROOT = Path("/home/rs/projects/opencs/ai-line-analysis")
RUN = ROOT / "temp/recovery-work/reconstruction10x10-20261121/packeting"
READ_MAP = RUN / "READ_INPUTS-post32-next-batch02-cycle21_g07-post32-next39-scoped01-dispatch02.json"
ELF_SHA = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
AUDIO = "_ZN8Presonus5Mixer14AudioComponentD2Ev"
DSP = "_ZN8Presonus12DspComponentD2Ev"
OUTERS = {
    "cycle21_g07_r07": ("_ZN8Presonus5Mixer17HPFilterComponentD0Ev", 0x3E0A8,
        "6960535783118fa15c924e2948bc8c153698fd73b7f2dbe04f8a18ac55f6aee1"),
    "cycle21_g07_r05": ("_ZN8Presonus5Mixer16LimiterComponentD0Ev", 0x3DFD8,
        "33c538f1c35d39b1018abea962bfa90b41011b298d503ded7a51b29a78772a97"),
}


def sha(value):
    return hashlib.sha256(value).hexdigest()


def execute(segments, ranges, entry, with_controller):
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    start = min(a for a, n, b in segments) & ~4095
    end = (max(a + n for a, n, b in segments) + 4095) & ~4095
    uc.mem_map(start, end - start)
    for a, _, b in segments:
        uc.mem_write(a, b)
    obj, property_obj, controller, stack, callbacks = (0x3000000 + i * 4096 for i in range(5))
    for address in (obj, property_obj, controller, stack, callbacks):
        uc.mem_map(address, 4096)
    put = lambda a, v: uc.mem_write(a, struct.pack("<I", v))
    get = lambda a: struct.unpack("<I", uc.mem_read(a, 4))[0]
    put(obj + 0xE4, property_obj)
    put(obj + 0xB0, controller if with_controller else 0)
    put(property_obj, property_obj + 0x20)
    put(property_obj + 0x28, callbacks)
    put(controller, controller + 0x20)
    put(controller + 0x28, callbacks + 4)
    uc.reg_write(UC_ARM_REG_R0, obj)
    uc.reg_write(UC_ARM_REG_SP, stack + 0x800)
    stop = callbacks + 8
    uc.reg_write(UC_ARM_REG_LR, stop)
    events = []

    def hook(machine, address, size, _):
        receiver = machine.reg_read(UC_ARM_REG_R0)
        after = machine.reg_read(UC_ARM_REG_LR)
        if address == stop:
            machine.emu_stop()
            return
        for identity, begin, end in ranges:
            if begin <= address < end:
                if address == begin:
                    assert receiver == obj
                    events.append(dict(operation=identity, address=address, caller_return=after))
                return
        if address == callbacks:
            assert receiver == property_obj and after == 0x3D330
            events.append(dict(operation="property release", address=address, caller_return=after))
        elif address == callbacks + 4:
            assert receiver == controller and after == 0x83168
            events.append(dict(operation="controller release", address=address, caller_return=after))
        elif address == 0x82FFC:
            assert receiver == obj and get(obj + 0xB0) == 0 and after == 0x83178
            events.append(dict(operation="Dsp base cleanup boundary", address=address, caller_return=after))
        elif address == 0xAC10:
            assert receiver == obj and after == entry + 44
            uc.mem_unmap(receiver, 4096)
            events.append(dict(operation="operator delete", address=address, caller_return=after))
        else:
            raise AssertionError(f"Unexpected native boundary {address:#x}")
        machine.reg_write(UC_ARM_REG_PC, after)

    uc.hook_add(UC_HOOK_CODE, hook)
    uc.emu_start(entry, stop + 4, count=1000)
    assert uc.reg_read(UC_ARM_REG_PC) == stop
    try:
        assert get(obj + 0xB0) == 0
        released = False
    except UcError:
        released = True
    assert released == (entry != 0x3D300)
    return dict(entry=entry, controller_present=with_controller, receiver_released=released, events=events)


def observe(task):
    mapping = json.loads(READ_MAP.read_text())["rootfs/RML16AI_Rack_13731/home/root/mixer"]
    path = Path(mapping["frozen_read_path"])
    file_bytes = path.read_bytes()
    assert sha(file_bytes) == mapping["sha256"] == ELF_SHA
    original, start, expected = OUTERS[task]
    spec = [[original, start, 56, expected],
            [AUDIO, 0x3D300, 88, "f8c7f7389ebf9d0d1c8c0f28e1e3b47d6156aae0e12714831d0370e3a93abf6b"],
            [DSP, 0x83130, 104, "62e6b0ffeca2c0fe8996e2816576896112eb56a6424499477abd3f0e34445ece"]]
    sections = []
    with path.open("rb") as fp:
        elf = ELFFile(fp)
        symbols = elf.get_section_by_name(".symtab")
        for identity, address, size, digest in spec:
            match = symbols.get_symbol_by_name(identity)
            assert len(match) == 1
            symbol = match[0]
            section = elf.get_section(symbol["st_shndx"])
            assert symbol["st_value"] == address and symbol["st_size"] == size
            offset = section["sh_offset"] + address - section["sh_addr"]
            assert sha(file_bytes[offset:offset + size]) == digest
            sections.append(dict(mangled=identity, address=address, size=size, section=section.name,
                                 file_offset=offset, range_sha256=digest))
        segments = [(s["p_vaddr"], s["p_memsz"], s.data())
                    for s in elf.iter_segments() if s["p_type"] == "PT_LOAD"]
    ranges = [(identity, address, address + size) for identity, address, size, digest in spec]
    cases = [execute(segments, ranges, entry, controller)
             for entry, controller in ((start, True), (0x3D300, True), (0x3D300, False))]
    return dict(task=task, elf_sha256=ELF_SHA, **sections[0], dependency_ranges=sections[1:],
                cases=cases, oracle="Original outer D0, Audio D2 and Dsp D2 instructions execute. "
                "Release methods and Dsp deep base cleanup are explicit controlled boundaries. "
                "The exact original delete PLT boundary releases the receive mapping.")


if __name__ == "__main__":
    print(json.dumps(observe(Path(__file__).parent.name), indent=2))
