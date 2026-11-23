"""Offline exact range and native direct/real-vtable replay for Actual06 G01."""
import argparse
import hashlib
import json
from pathlib import Path
from struct import pack, unpack

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc
from unicorn.arm_const import (UC_ARM_REG_LR as LR, UC_ARM_REG_PC as PC,
    UC_ARM_REG_R0 as R0, UC_ARM_REG_R1 as R1, UC_ARM_REG_R2 as R2,
    UC_ARM_REG_R3 as R3, UC_ARM_REG_SP as SP)

RECEIVER, STACK, STOP, ROUTE = (0x3000000, 0x4000000, 0x5000000, 0x6000000)
VARIANTS = ("r06", "r10", "s13", "s14", "s15", "s16", "s17", "s18", "s19")


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def capture(snapshot, reference, task):
    records = json.loads(reference.read_text())
    candidates = records["roles"].values() if "roles" in records else records["rows"]
    key = {
        "r06": "updateDisplayStyle", "r10": "updateLedColor",
        "s13": "getColorConverter", "s14": "setColorConverter",
        "s15": "onMappingParamChanged", "s16": "updatePanEncoderConnection",
        "s17": "onSelectionChanged", "s18": "onObjectChanged", "s19": "onComponentReplaced",
    }[task]
    all_observations = []
    for spec in candidates:
        body_spec = spec.get("body", spec)
        name = body_spec["original_mangled"]
        if key not in name:
            continue
        elf_hash = spec["elf_sha256"] if "roles" in records else records["source_elf"]["sha256"]
        role = "client" if elf_hash.startswith("304c6c") else "server"
        suffix = ("rootfs/CS18_v13840/home/root/surface" if role == "client"
                  else "rootfs/RML16AI_Rack_13731/home/root/mixer")
        path = snapshot / suffix
        assert sha(path) == elf_hash
        with path.open("rb") as f:
            elf = ELFFile(f)
            table = elf.get_section_by_name(".symtab")

            def exact(info):
                candidates = table.get_symbol_by_name(info["original_mangled"])
                assert len(candidates) == 1
                symbol = candidates[0]
                address, size, section_id = (symbol[k] for k in ("st_value", "st_size", "st_shndx"))
                section = elf.get_section(section_id)
                relative = address - section["sh_addr"]
                assert 0 <= relative <= section["sh_size"] - size
                offset = section["sh_offset"] + relative
                f.seek(offset)
                body = f.read(size)
                digest = hashlib.sha256(body).hexdigest()
                assert (address, size, offset, digest) == (
                    info["address"], info["size"],
                    info.get("file_offset", info.get("exact_file_offset")),
                    info.get("sha256", info.get("range_sha256")),
                )
                if "section" in info:
                    assert section.name == info["section"]
                return dict(address=address, size=size, file_offset=offset, section=section.name,
                            section_index=section_id, sha256=digest,
                            mangled=info["original_mangled"]), body

            target, body = exact(body_spec)
            chunks = [(target["address"], body)]
            vtable = typeinfo = None
            slot = None
            if "vtable" in spec:
                vtable, vtable_data = exact(spec["vtable"])
                typeinfo, typeinfo_data = exact(spec["typeinfo"])
                slot = spec["slot_vptr_relative"]
                assert unpack("<I", vtable_data[4:8])[0] == typeinfo["address"]
                assert unpack("<I", vtable_data[8 + slot:12 + slot])[0] == target["address"]
                chunks += [(vtable["address"], vtable_data), (typeinfo["address"], typeinfo_data)]

        color = "roles" in records
        cases = spec["cases"]
        observations = []
        for index, case in enumerate(cases):
            mode = "direct" if color or case["dispatch"] == "ordinary" else "vtable"
            uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
            pages = {RECEIVER, STACK, STOP, ROUTE}
            for addr, data in chunks:
                pages.update(range(addr & ~4095, ((addr + len(data) - 1) & ~4095) + 4096, 4096))
            for page in sorted(pages):
                uc.mem_map(page, 4096)
            for addr, data in chunks:
                uc.mem_write(addr, data)
            uc.mem_write(RECEIVER, bytes([((17 * index) + 7) % 256]) * 512)
            parameter = RECEIVER + 1024
            uc.mem_write(parameter, bytes(range(32)))
            args = ([case["input"], 12, 0] if color else
                    (list(case.get("entry_registers", {}).get(k, 0) for k in ("r1", "r2", "r3"))))
            if task in ("s15", "s19") and args[0] != 0:
                args[0] = parameter
            if color:
                uc.mem_write(RECEIVER + 36, pack("<I", case["initial_converter"]))
            if mode == "vtable":
                uc.mem_write(RECEIVER, pack("<I", vtable["address"] + 8))
                # ARM indirect call through the untouched real vtable.
                uc.mem_write(ROUTE, pack("<II", 0xE590C000, 0xE59CF000 | slot))
            before = bytes(uc.mem_read(RECEIVER, 512))
            for reg, value in zip((R0, R1, R2, R3), [RECEIVER, *args]):
                uc.reg_write(reg, value & 0xffffffff)
            uc.reg_write(SP, STACK + 0x800)
            uc.reg_write(LR, STOP)
            writes, trace = [], []

            def code(machine, addr, length, _):
                in_target = target["address"] <= addr < target["address"] + target["size"]
                assert in_target or (mode == "vtable" and addr in (ROUTE, ROUTE + 4)), hex(addr)
                trace.append(addr)

            def write(machine, access, addr, size, value, _):
                if not STACK <= addr < STACK + 4096:
                    writes.append([addr - RECEIVER, size, value])

            uc.hook_add(UC_HOOK_CODE, code)
            uc.hook_add(UC_HOOK_MEM_WRITE, write)
            uc.emu_start(ROUTE if mode == "vtable" else target["address"], STOP, count=64)
            assert uc.reg_read(PC) == STOP and target["address"] in trace
            assert bytes(uc.mem_read(parameter, 32)) == bytes(range(32))
            after = bytes(uc.mem_read(RECEIVER, 512))
            ret = uc.reg_read(R0)
            if task == "s14":
                assert writes == [[36, 4, case["effective_converter"]]]
                assert after == before[:36] + pack("<I", case["effective_converter"]) + before[40:]
            else:
                assert not writes and after == before
            if task == "s13":
                assert ret == case["effective_converter"]
            else:
                assert ret == RECEIVER
            observations.append(dict(dispatch=mode, args=args, trace=trace, writes=writes,
                                     r0=ret, receiver_preserved=after == before))
        all_observations.append(dict(elf_sha256=elf_hash, role=role, target=target,
                                     vtable=vtable, typeinfo=typeinfo, slot=slot,
                                     cases=observations))
    assert len(all_observations) == (2 if task in ("s13", "s14") else 1)
    return dict(task=task, reference_sha256=sha(reference), originals=all_observations)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("reference", type=Path)
    parser.add_argument("task", choices=VARIANTS)
    args = parser.parse_args()
    print(json.dumps(capture(args.snapshot, args.reference, args.task), indent=2))
