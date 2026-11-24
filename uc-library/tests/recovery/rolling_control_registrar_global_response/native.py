"""Execute a sealed ARM method and observe its bounded provider entry offline."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_SP,
)

RECEIVER = 0x1000000
TABLE = RECEIVER + 0x1000
MESSAGE = RECEIVER + 0x2000
SP = RECEIVER + 0x4000
RETURN = RECEIVER + 0x5000
VERSION_OFFSET = 0xA4
VERSION_BEFORE = 0xACDE
GLOBAL = Path(__file__).parent.name.endswith("global_response")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check_range(image, elf, target, evidence):
    section = elf.get_section(target["section"])
    assert section["sh_type"] == "SHT_PROGBITS"
    offset = section["sh_offset"] + target["address"] - section["sh_addr"]
    assert section["sh_offset"] <= offset
    assert offset + target["size"] <= section["sh_offset"] + section["sh_size"]
    assert offset == evidence["file_offset"]
    body = image[offset:offset + target["size"]]
    assert sha(body) == evidence["range_sha256"]
    return body


def put_code(cpu, pages, address, body):
    start = address & ~0xFFF
    end = (address + len(body) + 0xFFF) & ~0xFFF
    for page in range(start, end, 4096):
        if page not in pages:
            cpu.mem_map(page, 4096)
            pages.add(page)
    cpu.mem_write(address, body)


def observe(target, body, slot, provider, case):
    cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    pages = set()
    entry, callee = target["address"], slot["virtual_target"]
    put_code(cpu, pages, entry, body)
    bx_lr = bytes.fromhex("1eff2fe1")
    put_code(cpu, pages, callee, provider if GLOBAL else bx_lr)
    cpu.mem_map(RECEIVER, 0x6000)
    state = bytearray(b"\xa5" * 256)
    struct.pack_into("<I", state, 0, TABLE)
    struct.pack_into("<I", state, VERSION_OFFSET, VERSION_BEFORE)
    cpu.mem_write(RECEIVER, bytes(state))
    cpu.mem_write(TABLE + slot["slot"], struct.pack("<I", callee))
    payload = bytes(case["bytes"])
    cpu.mem_write(MESSAGE, payload)
    registers = {
        UC_ARM_REG_SP: SP,
        UC_ARM_REG_LR: RETURN,
        UC_ARM_REG_R0: RECEIVER,
        UC_ARM_REG_R1: case["type"] & 0xFFFFFFFF,
        UC_ARM_REG_R2: MESSAGE,
    }
    for register, value in registers.items():
        cpu.reg_write(register, value)
    calls = []

    def hook(uc, addr, length, _):
        if entry <= addr < entry + len(body):
            return
        if addr == callee:
            receiver, second, third = (uc.reg_read(register) for register in
                                       (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2))
            message = third if GLOBAL else second
            assert receiver == RECEIVER
            if GLOBAL:
                assert second == case["type"] & 0xFFFFFFFF and message == MESSAGE
            else:
                assert message == SP - 20
            calls.append({
                "receiver": receiver,
                "message": message,
                "target": addr,
                "type": second if GLOBAL else None,
                "bytes": list(uc.mem_read(message, 4)),
            })
            return
        assert GLOBAL and callee < addr < callee + len(provider), hex(addr)

    cpu.hook_add(UC_HOOK_CODE, hook)
    cpu.emu_start(entry, RETURN, count=64)
    assert cpu.reg_read(UC_ARM_REG_PC) == RETURN
    assert cpu.reg_read(UC_ARM_REG_SP) == SP
    assert bytes(cpu.mem_read(MESSAGE, 4)) == payload
    expected_calls = int(payload[1] == 0) if GLOBAL else 1
    assert len(calls) == expected_calls
    after = bytes(cpu.mem_read(RECEIVER, len(state)))
    if GLOBAL:
        assert after[:VERSION_OFFSET] == state[:VERSION_OFFSET]
        assert after[VERSION_OFFSET + 4:] == state[VERSION_OFFSET + 4:]
    else:
        assert after == state
    return {
        "input": case,
        "calls": calls,
        "version": struct.unpack_from("<I", after, VERSION_OFFSET)[0],
    }


def generate(preview, scan_elf, mixer_elf):
    images = {"client": scan_elf, "server": mixer_elf}
    originals = []
    for row in json.loads(preview.read_text())["originals"]:
        target, evidence, slot = row["target"], row["native"], row["slots"][0]
        image = images[target["role"]].read_bytes()
        assert sha(image) == target["original_elf_sha256"]
        elf = ELFFile(io.BytesIO(image))
        assert elf.little_endian and elf.get_machine_arch() == "ARM"
        body = check_range(image, elf, target, evidence)
        slot_address = slot["native_slot_address"]
        for section in elf.iter_sections():
            lower = section["sh_addr"]
            if section["sh_type"] != "SHT_NOBITS" and lower <= slot_address <= lower + section["sh_size"] - 4:
                slot_offset = section["sh_offset"] + slot_address - lower
                value = struct.unpack_from("<I", image, slot_offset)[0]
                assert value == slot["virtual_target"]
                break
        else:
            raise AssertionError("Slot outside ELF section")
        provider = b""
        provider_range = None
        if GLOBAL:
            provider_target, provider_evidence = row["actual_application_base"]
            assert provider_target["address"] == value
            provider = check_range(image, elf, provider_target, provider_evidence)
            provider_range = {
                "target": provider_target,
                "file_offset": provider_evidence["file_offset"],
                "range_sha256": sha(provider),
            }
        cases = [
            {"type": -17 if selector % 2 else 61,
             "bytes": [0x53, selector, selector ^ 0x5A, 0xC3]}
            for selector in range(256)
        ] if GLOBAL else [{"type": 0, "bytes": [0xA5] * 4}]
        originals.append({
            "target": target,
            "file_offset": evidence["file_offset"],
            "range_sha256": sha(body),
            "slot": slot,
            "slot_file_offset": slot_offset,
            "provider_range": provider_range,
            "cases": [observe(target, body, slot, provider, case) for case in cases],
        })
    return {"unicorn_version": unicorn.__version__, "originals": originals}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", type=Path, required=True)
    parser.add_argument("--surface", type=Path, required=True)
    parser.add_argument("--mixer", type=Path, required=True)
    output = parser.add_mutually_exclusive_group(required=True)
    output.add_argument("--out", type=Path)
    output.add_argument("--compare", type=Path)
    args = parser.parse_args()
    result = generate(args.preview, args.surface, args.mixer)
    if args.out:
        args.out.write_text(json.dumps(result, indent=2) + "\n")
    else:
        assert result == json.loads(args.compare.read_text())
        print(sum(len(row["cases"]) for row in result["originals"]), "exact ARM executions")


if __name__ == "__main__":
    main()
