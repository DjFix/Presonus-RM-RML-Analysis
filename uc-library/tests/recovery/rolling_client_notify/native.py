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
    target = witness["original"]
    elf, raw, result = row_evidence(target, witness, snapshot)
    table = symbol(elf, "_ZTVN8Presonus2UC15ClientComponentE")
    offset, data = read_range(elf, table)
    address_point = table["st_value"] + 8
    assert struct.unpack_from("<I", data, 8 + 48)[0] == target["address"]
    cases = []
    for seed in (0, 1, 5, 0x77, 0x80000000, 0xfeedbabe, 0xffffffff):
        # Receiver and typed argument stand-ins have separate initialized regions.
        vm = machine(target["address"], raw, (RECEIVER, PAYLOAD, seed, seed ^ 0xffffffff))
        receiver = struct.pack("<I", address_point) + bytes([seed & 255]) * 508
        payload = bytes([(seed ^ 0xff) & 255]) * 64
        vm.mem_write(RECEIVER, receiver)
        vm.mem_write(PAYLOAD, payload)
        trace = []
        vm.hook_add(u.UC_HOOK_MEM_READ | u.UC_HOOK_MEM_WRITE,
                    lambda cpu, access, addr, size, value, data:
                    trace.append([access, addr - STACK, size]))
        vm.emu_start(target["address"], STOP, count=12)
        assert vm.reg_read(PC) == STOP and vm.reg_read(SP) == STACK
        assert vm.reg_read(R0) == RECEIVER and vm.reg_read(R1) == PAYLOAD
        unchanged = (vm.mem_read(RECEIVER, 512) == receiver
                     and vm.mem_read(PAYLOAD, 64) == payload)
        assert unchanged and all(-16 <= addr < 0 for _, addr, _ in trace)
        cases.append(dict(output=str(int(unchanged)), seed=seed, stack=trace))
    return dict(result, cases=cases, vtable_address_point=address_point,
                vtable_slot=48, vtable_slot_file_offset=offset + 8 + 48)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    evidence = json.loads(args.evidence.read_text())
    name = "_ZN8Presonus2UC15ClientComponent6notifyERKNS0_17MessageAttributesE"
    observed = [execute(row, args.snapshot) for row in evidence
                if row["original"]["mangled"] == name]
    assert len(observed) == 2
    result = dict(originals=observed, engine=u.__version__,
                  receiver="Mapped distinct receiver and payload regions; native lifecycle excluded.")
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print("ARM notify cases:", sum(len(row["cases"]) for row in observed))


if __name__ == "__main__":
    main()
