"""Bounded synthetic call composition of existing EFM helpers, Linux only."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS
from unicorn.arm_const import (
    UC_CPU_ARM_CORTEX_M0, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2,
    UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_XPSR,
)

ROOT = Path('/home/rs/projects/opencs/ai-line-analysis')
OWN = ROOT / "uc-library/tools/recovery/efm-composition"
LIB = ROOT / "uc-library"
FADER = LIB / "candidates/efm-fader-app"
OUT = ROOT / "evidence/recovery/2026-10-27/efm-reconstruction/cross-layer/composition-01"
OUT.mkdir(parents=True, exist_ok=False)
START = time.monotonic()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(label, command, data=None):
    (OUT / (label + ".command.json")).write_text(json.dumps(command) + "\n")
    result = subprocess.run(command, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=ROOT)
    (OUT / (label + ".stdout")).write_bytes(result.stdout)
    (OUT / (label + ".stderr")).write_bytes(result.stderr)
    assert result.returncode == 0, (label, result.returncode)
    return result.stdout


image_path = ROOT / "evidence/recovery/2026-10-27/efm32-faders/fader-efm32-application-0x1000.bin"
assert sha(image_path) == "b87a39cea8ff234c0cca785a7c5433e4ff729d365b56fca05b3023caa3aa53b6"
for rel, expected in [
    ("validation/checks/native-01/validation.json", "327360c5349c92108a773b18435611218f75d2f5da2bb13c252324e1fa06b586"),
    ("validation/version/native-01/validation.json", "94e74590116f5d00554f6fc2bc8e4002d1384c90cb6d595d9363ee5c240d25af"),
]:
    assert sha(FADER / rel) == expected
    for path, digest in json.loads((FADER / rel).read_text())["source_hashes"].items():
        assert sha(ROOT / path) == digest, path

sources = [FADER / "src/efm_packet_checks.cpp", FADER / "src/efm_version_packet.cpp"]
headers = [FADER / "include/efm_packet_checks.hpp", FADER / "include/efm_version_packet.hpp"]
driver = OWN / "driver.cpp"
formatter = str(LIB / ".venv/bin/clang-format")
version = run("formatter-version", [formatter, "--version"]).decode().strip()
run("format-driver", [formatter, "--style=file", "--fallback-style=LLVM", "-i", str(driver)])
run("format-strict", [formatter, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror", *map(str, [driver] + sources + headers)])
binary = OUT / "composition-driver"
run("compile", ["c++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-I" + str(FADER / "include"), *map(str, sources), str(driver), "-o", str(binary)])

image = image_path.read_bytes()
arm = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
arm.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_M0)
arm.mem_map(0x1000, 0x4000)
arm.mem_write(0x1000, image)
arm.mem_map(0x20000000, 0x10000)
packet_address = 0x20001000


def call(address, r1=0, r2=0):
    arm.reg_write(UC_ARM_REG_SP, 0x2000f000)
    arm.reg_write(UC_ARM_REG_LR, 0x4001)
    arm.reg_write(UC_ARM_REG_XPSR, 0x01000000)
    arm.reg_write(UC_ARM_REG_R0, packet_address)
    arm.reg_write(UC_ARM_REG_R1, r1)
    arm.reg_write(UC_ARM_REG_R2, r2)
    arm.emu_start(address | 1, 0x4000, count=20000)
    assert arm.reg_read(UC_ARM_REG_PC) == 0x4000
    return arm.reg_read(UC_ARM_REG_R0)


rows, expected, examples = [], [], []
for board in range(4):
    for high in (board, 15):
        for selector in range(16):
            for length in (0, 4, 255):
                for seed in (0xa5, 0x5a):
                    packet = bytearray((seed + i * 37) & 255 for i in range(320))
                    packet[:3] = bytes([(high << 4) | selector, 0xa5, length])
                    a = b = 0
                    for byte in packet[:3]:
                        a = (a + byte) % 255
                        b = (b + a) % 255
                    packet[3:5] = bytes([a, b])
                    arm.mem_write(packet_address, bytes(packet))
                    arm.mem_write(0x200001d4, bytes([board]))
                    assert call(0x2a84) == 0
                    call(0x2230, 0x20002000, 0)
                    call(0x2a24)
                    after = bytes(arm.mem_read(packet_address, len(packet)))
                    rows.append(f"{board} {packet.hex()}\n")
                    expected.append("0 " + after.hex() + "\n")
                    if board == high == 0 and selector in (0, 1, 2, 15) and length == 0 and seed == 0xa5:
                        examples.append({"selector": selector, "request_prefix": packet[:5].hex(), "response_length": after[2], "announced_prefix": after[:after[2] + 5].hex(), "full_buffer_sha256": hashlib.sha256(after).hexdigest()})

stdin = "".join(rows).encode()
witness = "".join(expected).encode()
(OUT / "fixtures.stdin").write_bytes(stdin)
(OUT / "arm-output.txt").write_bytes(witness)
native = run("native", [str(binary)], stdin)
assert native == witness, "Composition mismatch: retained original/native output"
proof = {
    "passed": True,
    "image_sha256": sha(image_path),
    "cases": len(rows),
    "domain": "4 seeded board IDs x matching/broadcast high nibble x 16 selectors x request lengths 0/4/255 x 2 tail patterns; full 320-byte buffers",
    "call_sequence": ["0x2a84 validate read-header checks", "0x2230 partial command 0xa5 dispatcher", "0x2a24 append response checks"],
    "synthetic_call_composition": True,
    "scope_limits": "Explicit independent helper call sequence, not execution of the receive IRQ, transmit FSM, outer query, peripheral or physical device. Prefix is selected by the observed length field; transport completion not proved.",
    "original_cpu_model": "Cortex-M0 ARMv6-M",
    "original_helpers_hooked": False,
    "peripherals_emulated": False,
    "hardware_accessed": False,
    "examples": examples,
    "formatter": version,
    "source_hashes": {str(p.relative_to(ROOT)): sha(p) for p in [driver] + sources + headers},
    "tool_sha256": sha(Path(__file__)),
    "artifacts": {p.name: sha(p) for p in OUT.iterdir() if p.is_file()},
    "elapsed_seconds": time.monotonic() - START,
}
snapshot = OUT / "sources"
for path in [driver, Path(__file__)] + sources + headers:
    target = snapshot / path.relative_to(ROOT)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, target)
(OUT / "validation.json").write_text(json.dumps(proof, indent=2) + "\n")
print(json.dumps({"passed": True, "cases": len(rows), "examples": examples, "proof_sha256": sha(OUT / "validation.json")}))
