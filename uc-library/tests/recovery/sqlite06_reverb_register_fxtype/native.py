"""Observe the exact ARM initializer and dispatch through its formatter slots."""
import json
from pathlib import Path
import runpy
import struct

from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc, __version__
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2

HERE = Path(__file__).parent
RUNTIME = runpy.run_path(str(HERE.parent / "sqlite06_reverb_fxtype_deleting_destroy/native.py"))
PRINT_PATH = HERE.parent / "cycle20_g09_s08/native.py"
REGISTRATION = "sqlite06_reverb_register_fxtype"
CASES = [(0, 32), (1, 8), (4, 2), (7, 1), (7, 0), (7, 32)]


def replay(original, bindings):
    app = RUNTIME["Image"](Path(original["elf_path"]), original["elf"])
    arm = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    app.load(arm)
    arm.mem_map(0x71000000, 0x10000)
    body = RUNTIME["verified_body"](app, arm, original)
    guard, receiver, name, vptr, destructor, dso = struct.unpack_from("<6I", body, 112)
    prefix = original["mangled"]
    assert guard == app.symbol(f"_ZGVZ{prefix[2:]}E12theFormatter", ".symtab")["st_value"]
    assert receiver == app.symbol(f"_ZZ{prefix[2:]}E12theFormatter", ".symtab")["st_value"]
    assert vptr == app.symbol("_ZTVN8Presonus5Mixer15FxTypeFormatterE", ".symtab")["st_value"] + 8
    assert destructor == app.symbol("_ZN8Presonus5Mixer15FxTypeFormatterD1Ev", ".symtab")["st_value"]
    word = RUNTIME["word"]
    put = RUNTIME["put"]
    assert word(arm, guard) == 0 and bytes(arm.mem_read(receiver, 12)) == bytes(12)
    effects, writes = [], []

    def register_boundary(cpu, pc, _size, routine):
        r0, r1, r2 = [cpu.reg_read(reg) for reg in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2)]
        if routine == "acquire":
            assert r0 == guard and word(cpu, guard) == 0
            cpu.reg_write(UC_ARM_REG_R0, 1)
        elif routine == "release":
            assert r0 == guard and word(cpu, guard) == 0
            assert word(cpu, receiver) == vptr and word(cpu, receiver + 4) == name
            put(cpu, guard, 1)
        elif routine == "atexit":
            assert (r0, r1, r2) == (receiver, destructor, dso)
            cpu.reg_write(UC_ARM_REG_R0, 0)
        else:
            assert r0 == receiver and word(cpu, guard) == 1
            assert word(cpu, r0) == vptr and word(cpu, r0 + 4) == name
        effects.append({"routine": routine, "pc": pc, "receiver_argument": r0})
        cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))

    def record_write(_cpu, _access, address, size, value, _data):
        writes.append([address - receiver, size, value])

    for offset, routine in ((36, "add"), (44, "acquire"), (88, "release"), (104, "atexit")):
        target = next(row["value"] for row in bindings if row["offset"] == offset)
        arm.hook_add(UC_HOOK_CODE, register_boundary, routine, begin=target, end=target)
    arm.hook_add(UC_HOOK_MEM_WRITE, record_write, begin=receiver, end=receiver + 11)

    call = RUNTIME["call"]
    for seed in (0, 0xffffffff, 0x12345678):
        call(arm, original["address"], seed)
    assert [event["routine"] for event in effects] == ["acquire", "release", "atexit", "add", "add", "add"]
    observed_name = RUNTIME["read_string"](arm, word(arm, receiver + 4))
    style, = arm.mem_read(receiver + 8, 1)
    assert writes == [[4, 4, name], [8, 1, style], [0, 4, vptr]]

    namespace = runpy.run_path(str(PRINT_PATH))
    printer = next(row for row in namespace["TARGETS"] if row["elf_sha256"] == original["elf"])
    print_slot = word(arm, vptr + 8)
    scan_slot = word(arm, vptr + 12)
    assert print_slot == printer["original_address"]
    scan_symbol = app.symbol("_ZNK8Presonus5Mixer15NumberPrepender4scanERN4Core9Formatter4DataE", ".symtab")
    assert scan_slot == scan_symbol["st_value"]
    scan_section = app.elf.get_section(scan_symbol["st_shndx"])
    scan_offset = scan_section["sh_offset"] + scan_slot - scan_section["sh_addr"]
    scan_body = app.data[scan_offset:scan_offset + scan_symbol["st_size"]]
    assert scan_body == bytes(arm.mem_read(scan_slot, len(scan_body)))
    data = 0x71000000
    unchanged = bytes(range(20))
    arm.mem_write(data, unchanged)
    arm.reg_write(UC_ARM_REG_R1, data)
    scan_result = call(arm, scan_slot, receiver)
    assert scan_result == 0 and bytes(arm.mem_read(data, len(unchanged))) == unchanged

    # Use the existing independent ARM print oracle, supplying this formatter's
    # observed prefix and verified vtable slot. Its runtime boundary is finite.
    print_replay = namespace["replay"]
    print_replay.__globals__["cases"] = [(value, style, capacity) for value, capacity in CASES]
    imports = {address: namespace["helper_name"](names) for address, names in printer["call_targets"].items()}
    printing = print_replay(app.elf, printer, printer["mangled"], namespace["data_provider"](app.elf), imports)
    printing["modeled_boundaries"] = {str(address): name for address, name in imports.items()}
    return {
        "original": original, "name": observed_name, "style": style, "static_receiver": receiver,
        "effects": effects, "initializer_writes": writes, "scan": scan_result,
        "scan_slot": scan_slot, "scan_file_offset": scan_offset,
        "scan_size": scan_symbol["st_size"], "scan_range_sha256": RUNTIME["digest"](scan_body),
        "unicorn_version": __version__, "printing": printing,
    }


def generate():
    context = json.loads((RUNTIME["ISSUED"] / REGISTRATION / "CONTEXT.json").read_text())
    evidence = context["task"]["review"]["equivalence"]
    bound = Path(evidence["path"]).read_bytes()
    assert RUNTIME["digest"](bound) == evidence["sha256"]
    bindings = {row["elf"]: row["address_dependent_bindings"] for row in json.loads(bound)["originals"]}
    return [replay(original, bindings[original["elf"]]) for original in RUNTIME["originals"](REGISTRATION)]


if __name__ == "__main__":
    RUNTIME["cli"](generate)
