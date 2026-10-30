#!/usr/bin/env python3
"""Fresh bounded RM ARM replay against existing shared production fixtures."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import struct
import subprocess

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert platform.system() == "Linux"
    repo = Path.cwd().resolve()
    lib = repo / "uc-library"
    out = repo / "temp/recovery-work/avb-rm-helpers/fresh-01"
    out.mkdir(parents=True, exist_ok=False)
    fixtures = lib / "validation/avb-protocol/runs/20261026T235518.530958Z"
    old = json.loads((fixtures / "arm-oracle.json").read_text())
    manifest = json.loads((lib / "recovered-all/server/manifest.json").read_text())
    binary = repo / manifest["path"]
    assert digest(binary) == manifest["sha256"]
    names = {key: old["functions"][key]["mangled"] for key in ("R", "U")}
    symbols = json.loads((lib / "recovered-all/server/all-symbols.json").read_text())
    rows = {}
    raw = binary.read_bytes()
    with binary.open("rb") as stream:
        elf = ELFFile(stream)
        for key, name in names.items():
            matches = [row for row in symbols if row["mangled"] == name and row["size"]]
            assert len(matches) == 1
            row = dict(matches[0])
            section = elf.get_section(row["section"])
            offset = section["sh_offset"] + row["address"] - section["sh_addr"]
            assert section["sh_addr"] <= row["address"] < row["address"] + row["size"] <= section["sh_addr"] + section["sh_size"]
            code = raw[offset:offset + row["size"]]
            assert hashlib.sha256(code).hexdigest() == old["functions"][key]["sha256"]
            row.update(file_offset=offset, sha256=hashlib.sha256(code).hexdigest(), original_elf_sha256=manifest["sha256"], role="server")
            rows[key] = row
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    uc.mem_map(0xA0000, 0x10000)
    for row in rows.values():
        uc.mem_write(row["address"], raw[row["file_offset"]:row["file_offset"] + row["size"]])
    uc.mem_map(0x100000, 0x20000)
    uc.mem_map(0x200000, 0x1000)
    stop, arena = 0x200000, 0x101000

    def call(key, registers):
        uc.reg_write(UC_ARM_REG_SP, 0x11F000)
        uc.reg_write(UC_ARM_REG_LR, stop)
        for reg, value in zip((UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3), registers):
            uc.reg_write(reg, value & 0xFFFFFFFF)
        uc.emu_start(rows[key]["address"], stop, count=10000)
        assert uc.reg_read(UC_ARM_REG_PC) == stop, "bounded execution did not return"
        return uc.reg_read(UC_ARM_REG_R0), uc.reg_read(UC_ARM_REG_R1)

    counts = {"R": 0, "U": 0}
    for line in (fixtures / "reverse-vectors.txt").read_text().splitlines():
        value, expected = (int(word, 16) for word in line.split())
        lo, hi = call("R", (0x110000, 0, value & 0xFFFFFFFF, value >> 32))
        assert (hi << 32) | lo == expected
        counts["R"] += 1
    with gzip.open(fixtures / "memory-vectors.bin.gz", "rb") as stream:
        while operation := stream.read(1):
            header = stream.read(16)
            assert len(header) == 16
            length, source, destination, expected = struct.unpack("<4I", header)
            before, after = stream.read(512), stream.read(512)
            assert len(before) == len(after) == 512
            if operation != b"U":
                continue
            uc.mem_write(arena, before)
            result, _ = call("U", (0x110000, 0 if destination == 0xFFFFFFFF else arena + destination, 0 if source == 0xFFFFFFFF else arena + source, length))
            assert result == expected
            assert bytes(uc.mem_read(arena, 512)) == after
            counts["U"] += 1
    assert all(counts.values())
    command = [str(repo / "temp/core-upstream/root-integration-01/avb_protocol_tests"), *map(str, (fixtures / name for name in ("accept-vectors.txt", "reverse-vectors.txt", "memory-vectors.bin.gz")))]
    completed = subprocess.run(command, capture_output=True, text=True, env=dict(os.environ, TMPDIR=str(out)))
    (out / "native-replay.log").write_text(repr(command) + "\n" + completed.stdout + completed.stderr)
    assert completed.returncode == 0
    proof = dict(status="fresh RM ARM + active shared native fixture replay; not admitted", functions=list(rows.values()), counts=counts, native_stdout=completed.stdout, binary_sha256=digest(Path(command[0])), fixtures={str((fixtures / name).relative_to(lib)):digest(fixtures / name) for name in ("arm-oracle.json", "reverse-vectors.txt", "memory-vectors.bin.gz")}, tool_sha256=digest(Path(__file__)), hardware_verified=False, arm_abi_verified=False, limitations=["Existing fixture domain only; no readiness admission or claim of complete AvbManagerBase object layout."])
    (out / "validation.json").write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps({"output":str(out), "counts":counts, "native":completed.stdout.strip()}))


if __name__ == "__main__":
    main()
