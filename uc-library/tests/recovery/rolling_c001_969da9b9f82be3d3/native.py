import argparse
import hashlib
import io
import json
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn import arm_const


def observe(path, identity):
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == identity["elf_sha256"]
    elf = ELFFile(io.BytesIO(raw))
    symbol, = elf.get_section_by_name(".symtab").get_symbol_by_name(identity["mangled"])
    address, size, index = (symbol[key] for key in ("st_value", "st_size", "st_shndx"))
    assert (address, size, index) == (identity["address"], identity["size"], 12)
    section = elf.get_section(index)
    assert section.name == identity["section"]
    position = address - section["sh_addr"]
    assert 0 <= position <= section["sh_size"] - size
    offset = section["sh_offset"] + position
    code = raw[offset:offset + size]
    digest = hashlib.sha256(code).hexdigest()
    assert digest == "60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad"

    cases = []
    for marker in (0, 0xffffffff, 0x12345678):
        uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        code_page = address & ~0xfff
        stack, data, sentinel = 0x200000, 0x300000, 0x400000
        for page in (code_page, stack, data, sentinel):
            uc.mem_map(page, 4096)
        uc.mem_write(address, code)
        payload = marker.to_bytes(4, "little") * 1024
        uc.mem_write(data, payload)
        registers = [getattr(arm_const, f"UC_ARM_REG_R{i}") for i in range(13)]
        registers.extend((arm_const.UC_ARM_REG_SP, arm_const.UC_ARM_REG_LR))
        values = [data + (marker & 0x3c), data + 0x100 + (marker & 0x3c)]
        values.extend((marker ^ i) for i in range(2, 13))
        sp = stack + 0x800
        values.extend((sp, sentinel))
        for reg, value in zip(registers, values):
            uc.reg_write(reg, value)
        accesses = []
        uc.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE,
                    lambda _, access, where, width, value, __: accesses.append([access, where, width]))
        uc.emu_start(address, sentinel, count=8)
        assert uc.reg_read(arm_const.UC_ARM_REG_PC) == sentinel
        final = [uc.reg_read(reg) for reg in registers]
        assert final[:12] == values[:12] and final[13:] == values[13:]
        assert final[12] == sp
        assert accesses and all(sp - 16 <= where <= sp - width
                                for _, where, width in accesses)
        cases.append(dict(marker=marker, registers_before=values, registers_after=final,
                          accesses=accesses, state_changed=bytes(uc.mem_read(data, 4096)) != payload))
    return dict(range=dict(identity, file_offset=offset, range_sha256=digest), cases=cases)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--elf", required=True, type=Path)
    parser.add_argument("--fixtures", required=True, type=Path)
    parser.add_argument("--generate", action="store_true")
    args = parser.parse_args()
    identity = dict(elf_sha256="9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07",
                    mangled="_ZN8Presonus5Mixer22MasterSectionComponent16processLinkEventERNS_8Intercom9LinkEventE",
                    address=0x48fe8, size=16, section=".text", section_index=12,
                    role="server", firmware="RM/RML mixer 13731")
    observation = observe(args.elf, identity)
    if args.generate:
        args.fixtures.write_text(json.dumps(observation, indent=2) + "\n")
    else:
        assert observation == json.loads(args.fixtures.read_text())
    print(f"{len(observation['cases'])} independent original ARM executions")
