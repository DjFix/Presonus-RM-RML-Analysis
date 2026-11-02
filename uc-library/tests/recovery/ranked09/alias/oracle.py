"""Execute exact AliasComponent ARM ranges, isolating the pinned Core boundary.

The provider call is captured and returned without pretending to execute Core.
Object writes below therefore describe only the original application body.
"""
import hashlib
import json
from pathlib import Path
import unicorn
from elftools.elf.elffile import ELFFile
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_LR, UC_ARM_REG_SP, UC_ARM_REG_PC

ROOT = Path(__file__).resolve().parents[5]
SUPPLEMENT = ROOT / 'temp/recovery-work/ranked-trial-09-small01/supplements/alias-table/MANIFEST.json'
ELF = ROOT / "rootfs/RML16AI_Rack_13731/home/root/mixer"
SHA = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
TARGETS = [("C2", 0x39B70, "aa9859b3a7a78bd722f57b079ce180002fa9c5bfb26450215f201256f389d136"), ("C1", 0x39B34, "7c4617173e7aed8c31daf01dcf130bcb520c504ec86627bb402ceda9ed2365b2")]


def main():
    blob = ELF.read_bytes()
    assert hashlib.sha256(blob).hexdigest() == SHA
    ranges, cases, lifecycle = [], [], []
    supplement = json.loads(SUPPLEMENT.read_text())
    # Bind each supplemental static range independently. These methods gain no
    # reconstruction or readiness status from constructor replay.
    for item in supplement['originals']:
        body = item['native_body']
        assert hashlib.sha256(blob[body['file_offset']:body['file_offset'] + body['size']]).hexdigest() == body['bytes_sha256']
    with ELF.open("rb") as stream:
        ef = ELFFile(stream)
        section = ef.get_section(12)
        assert section.name == ".text"
        for variant, address, expected in TARGETS:
            offset = int(section["sh_offset"]) + address - int(section["sh_addr"])
            digest = hashlib.sha256(blob[offset:offset + 60]).hexdigest()
            assert digest == expected
            ranges.append(dict(mangled=f"_ZN8Presonus14AliasComponent{variant}EPKc", address=address, size=60, section=".text", file_offset=offset, sha256=digest))
            for fill in (0, 0xA5, 0xFF):
                for name in ("", "alias", "Channel 32"):
                    uc = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
                    uc.mem_map(0, 0x500000)
                    for segment in ef.iter_segments():
                        if segment["p_type"] == "PT_LOAD":
                            base, size = int(segment["p_vaddr"]), int(segment["p_filesz"])
                            uc.mem_write(base, segment.data())
                    uc.mem_map(0x1000000, 0x10000)
                    obj, text, stop = 0x1001000, 0x1002000, 0x1003000
                    uc.mem_write(obj, bytes([fill]) * 256)
                    uc.mem_write(text, name.encode() + b"\0")
                    uc.reg_write(UC_ARM_REG_R0, obj)
                    uc.reg_write(UC_ARM_REG_R1, text)
                    uc.reg_write(UC_ARM_REG_SP, 0x100F000)
                    uc.reg_write(UC_ARM_REG_LR, stop)
                    calls, writes = [], []

                    def code_hook(machine, pc, size, unused):
                        if pc in (0x119E8C, 0x11A53C):
                            if pc == 0x119E8C:
                                calls.append(dict(target="Core::Portable::Component::Component(char const*)", this=machine.reg_read(UC_ARM_REG_R0) - obj, name_pointer=machine.reg_read(UC_ARM_REG_R1) - text))
                            else:
                                calls.append(dict(target="Core::Portable::Component::~Component()", this=machine.reg_read(UC_ARM_REG_R0) - obj))
                            machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

                    def write_hook(machine, access, address, size, value, unused):
                        if obj <= address < obj + 256:
                            writes.append(dict(offset=address - obj, size=size, value=value))

                    uc.hook_add(unicorn.UC_HOOK_CODE, code_hook)
                    uc.hook_add(unicorn.UC_HOOK_MEM_WRITE, write_hook)
                    uc.emu_start(address, stop, count=100)
                    assert uc.reg_read(UC_ARM_REG_PC) == stop
                    cases.append(dict(variant=variant, fill=fill, name=name, calls=calls, writes=writes, returned_this=uc.reg_read(UC_ARM_REG_R0) == obj, object_hex=bytes(uc.mem_read(obj, 256)).hex()))
                    # Getter and non-deleting destructor observations establish
                    # the app pointer boundary without reconstructing providers.
                    uc.mem_write(obj + 132, text.to_bytes(4, 'little'))
                    uc.reg_write(UC_ARM_REG_R0, obj)
                    uc.reg_write(UC_ARM_REG_LR, stop)
                    uc.emu_start(0x39908, stop, count=100)
                    assert uc.reg_read(UC_ARM_REG_R0) == text
                    calls, writes = [], []
                    uc.reg_write(UC_ARM_REG_R0, obj)
                    uc.reg_write(UC_ARM_REG_LR, stop)
                    uc.emu_start(0x39AD4 if variant == 'C1' else 0x39B04, stop, count=100)
                    assert uc.reg_read(UC_ARM_REG_PC) == stop
                    lifecycle.append(dict(constructor_variant=variant, destructor_variant='D1' if variant == 'C1' else 'D2', getter_returned_injected_pointer=True, calls=calls, writes=writes, pointer_unchanged=int.from_bytes(uc.mem_read(obj + 132, 4), 'little') == text))
    out = dict(elf_sha256=SHA, unicorn_version=unicorn.__version__, ranges=ranges, cases=cases, lifecycle=lifecycle, supplement_sha256=hashlib.sha256(SUPPLEMENT.read_bytes()).hexdigest(), domain="18 original ARM constructors plus 18 getters and 18 D1/D2 app bodies; provider boundaries captured, not executed; original application memory writes only", limitations=["Core constructor/destructor boundaries returned without mutation; no provider binary recovery", "Original field declaration, complete lifecycle, layout, ARM ABI and hardware remain unresolved; typed setOriginal argument supports source-port pointer choice", "D0 deletion not executed or claimed"])
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
