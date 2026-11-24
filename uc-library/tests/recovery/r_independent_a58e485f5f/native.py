import argparse
import hashlib
import io
import json
import struct
from pathlib import Path

import unicorn as u
from elftools.elf.elffile import ELFFile
from unicorn.arm_const import (
    UC_ARM_REG_LR as LR, UC_ARM_REG_PC as PC, UC_ARM_REG_SP as SP,
    UC_ARM_REG_R0 as R0, UC_ARM_REG_R1 as R1, UC_ARM_REG_R2 as R2,
    UC_ARM_REG_R3 as R3,
)

RECEIVER = 0x51000000
PAYLOAD = 0x51000600
HANDLER = 0x51000500
STACK = 0x52000F00
STOP = 0x53000000


def sha(data):
    return hashlib.sha256(data).hexdigest()


def symbol(elf, name):
    matches = elf.get_section_by_name(".symtab").get_symbol_by_name(name)
    assert len(matches) == 1, name
    return matches[0]


def read_range(elf, sym):
    section = elf.get_section(sym["st_shndx"])
    relative = sym["st_value"] - section["sh_addr"]
    size = sym["st_size"]
    assert 0 <= relative <= relative + size <= section["sh_size"]
    raw = section.data()[relative:relative + size]
    return section["sh_offset"] + relative, raw


def native_elf(snapshot, witness):
    ref = witness["native"]["source_elf"]
    data = (snapshot / ref["path"]).read_bytes()
    assert sha(data) == ref["sha256"]
    return ELFFile(io.BytesIO(data)), ref


def machine(start, raw, args, targets=()):
    vm = u.Uc(u.UC_ARCH_ARM, u.UC_MODE_ARM)
    for page in {address & ~4095 for address in
                 (start, start + len(raw) - 1, RECEIVER, STACK, STOP, *targets)}:
        vm.mem_map(page, 4096)
    vm.mem_write(start, raw)
    for reg, value in zip((R0, R1, R2, R3, SP, LR), (*args, STACK, STOP)):
        vm.reg_write(reg, value)
    return vm


def word(vm, address):
    return struct.unpack("<I", vm.mem_read(address, 4))[0]


def row_evidence(target, witness, snapshot):
    elf, ref = native_elf(snapshot, witness)
    sym = symbol(elf, target["mangled"])
    assert elf["e_machine"] == "EM_ARM" and elf.elfclass == 32
    assert (sym["st_value"], sym["st_size"], sym["st_shndx"]) == (
        target["address"], target["size"], target["section"])
    offset, raw = read_range(elf, sym)
    assert offset == witness["native"]["file_offset"]
    assert sha(raw) == witness["native"]["range_sha256"]
    assert target["original_elf_sha256"] == ref["sha256"]
    return elf, raw, dict(target=target, source_elf=ref,
                          file_offset=offset, range_sha256=sha(raw))


def execute(witness, snapshot):
    target = witness["target"]
    elf, raw, result = row_evidence(target, witness, snapshot)
    calls = {int(address): name for address, name in witness["observed_providers"].items()}
    for address, name in calls.items():
        assert symbol(elf, name)["st_value"] == address
    table = symbol(elf, "_ZTVN8Presonus2UC11LocalServerE")["st_value"]
    cases = []
    for sample in witness["cases"]:
        handler = HANDLER if sample["has_handler"] else 0
        vm = machine(target["address"], raw,
                     (RECEIVER, sample["id"], handler, PAYLOAD), calls)
        vm.mem_write(RECEIVER, b"\xa5" * 512)
        writes = []
        trace = []

        def call(cpu, address, size, data):
            if address in calls:
                assert cpu.reg_read(R0) == RECEIVER
                if "setInfo" in calls[address]:
                    assert cpu.reg_read(R1) == PAYLOAD
                trace.append(calls[address])
                cpu.reg_write(PC, cpu.reg_read(LR))

        def write(cpu, access, address, size, value, data):
            if RECEIVER <= address < RECEIVER + 512:
                writes.append([address - RECEIVER, size, value])

        vm.hook_add(u.UC_HOOK_CODE, call)
        vm.hook_add(u.UC_HOOK_MEM_WRITE, write)
        vm.emu_start(target["address"], STOP, count=120)
        assert vm.reg_read(PC) == STOP and vm.reg_read(SP) == STACK
        assert vm.reg_read(R0) == RECEIVER and trace == sample["call_sequence"]
        assert word(vm, RECEIVER) == table + 8
        observed_id = word(vm, RECEIVER + 0x108)
        observed_handler = word(vm, RECEIVER + 0x124)
        observed_byte = vm.mem_read(RECEIVER + 0x128, 1)[0]
        assert observed_id == sample["id"] and observed_handler == handler
        assert observed_byte == 0
        assert writes == [[0, 4, table + 8], [0x124, 4, handler],
                          [0x128, 1, 0], [0x108, 4, observed_id]]
        cases.append(dict(output=f"{observed_id} {int(bool(observed_handler))} {observed_byte}",
                          writes=writes, providers=trace))
    return dict(result, cases=cases, vtable_address_point=table + 8)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    evidence = json.loads(args.evidence.read_text())
    observed = [execute(row, args.snapshot) for row in evidence["originals"]]
    result = dict(originals=observed, engine=u.__version__,
                  provider_boundary="ARM Server C2 and setInfo entry stubs; actual portable providers exercised separately.")
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print("ARM constructor cases:", sum(len(row["cases"]) for row in observed))


if __name__ == "__main__":
    main()
