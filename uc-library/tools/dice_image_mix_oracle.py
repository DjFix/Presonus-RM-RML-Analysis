#!/usr/bin/env python3
"""Bounded ARM mixer execution against emulated RAM registers, never devices."""
import argparse
import gzip
import hashlib
import json
import re
import struct
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_BLOCK, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC

IMAGE_SHA = "0468d888f3d615e70065f5d535b9eadac7f8bf67185b53cc19c2cb7986c1d946"
RANGES = {"dump": (0x140b4, 0x14134, 0x14158), "clrin": (0x14158, 0x141a4, 0x141ac),
          "clrout": (0x141ac, 0x141f8, 0x14200), "gain": (0x14200, 0x14250, 0x14258),
          "cfg": (0x14258, 0x142e0, 0x142e8)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("repository", type=Path)
    args = p.parse_args()
    lib = args.repository.resolve() / "uc-library"
    out = lib / "validation/dice-image/mix-runs" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out.mkdir(parents=True, exist_ok=False)
    image = (lib / "recovered-dice/client/data/001ab7ac-38470.bin").read_bytes()
    assert hashlib.sha256(image).hexdigest() == IMAGE_SHA
    assert image[:4] == b"TCAT" and struct.unpack_from("<I", image, 8)[0] == 0x200
    u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    u.mem_map(0, 0x50000)
    u.mem_write(0x200, image[16:])
    u.mem_map(0x10000000, 0x10000)
    u.mem_map(0x20000000, 0x1000)
    u.mem_map(0xc4000000, 0x1000)  # Pure emulated RAM. No physical MMIO.
    blocks = set()
    hook_counts = Counter()
    state = {}

    def event(text):
        state["events"] += 1
        state["trace"].append(text)
        for byte in (text + "\n").encode():
            state["hash"] = ((state["hash"] ^ byte) * 1099511628211) & 0xffffffffffffffff
        if len(state["sample"]) < 40:
            state["sample"].append(text)

    def cstring(address):
        raw = bytearray()
        for offset in range(4096):
            value = bytes(u.mem_read(address + offset, 1))
            if value == b"\0":
                return raw.decode("ascii")
            raw.extend(value)
        raise RuntimeError("unterminated string")

    def external(uc, address, size, unused):
        r0, r1, r2 = [uc.reg_read(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2)]
        if address == 0x17f30:
            hook_counts["diagnostic"] += 1
            event(f'D {r0} {r1} {cstring(r2).encode().hex()}')
        elif address == 0x180c8:
            hook_counts["printf"] += 1
            fmt = cstring(r0)
            arguments = iter((r1, r2))
            def substitute(match):
                value = next(arguments)
                return cstring(value) if match[0] == "%s" else (f"{value:08x}" if match[0] == "%08x" else str(value))
            text = re.sub(r"%08x|%u|%s", substitute, fmt)
            assert "%" not in text
            event("P " + text.encode().hex())
        else:
            raise RuntimeError(f"unmodeled external 0x{address:x}")
        # Explicit normal-return hook contract. Caller-saved results are unused.
        uc.reg_write(UC_ARM_REG_R0, 0)
        uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

    def memory(uc, access, address, size, value, unused):
        assert size == 4 and address in (0xc4000200, 0xc4000204, 0xc400020c)
        if access == unicorn.UC_MEM_READ:
            value = int.from_bytes(uc.mem_read(address, 4), "little")
            event(f"R {address} {value}")
        else:
            event(f"W {address} {value & 0xffffffff}")

    def block(uc, address, size, unused):
        if address in (0x17f30, 0x180c8):
            return
        assert any(start <= address < code_end for start, code_end, pool_end in RANGES.values()), hex(address)
        blocks.add(address)

    u.hook_add(UC_HOOK_CODE, external, begin=0x17f30, end=0x17f30)
    u.hook_add(UC_HOOK_CODE, external, begin=0x180c8, end=0x180c8)
    u.hook_add(UC_HOOK_BLOCK, block)
    u.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, memory, begin=0xc4000200, end=0xc400020f)

    def inputs():
        indices = list(range(34)) + [255, 0x7fffffff, 0x80000000, 0xffffffff]
        for name in ("clrin", "clrout"):
            for a in indices:
                yield name, a, 0, 0, 0, 0
        gains = [0, 1, 0x7fff, 0x8000, 0xffff, 0x10000, 0x12345678, 0xffffffff]
        for a in indices:
            for b in indices:
                for c in gains:
                    yield "gain", a, b, c, 0, 0
        for a in range(34):
            for b in range(34):
                for c in (0, 1):
                    yield "cfg", a, b, c, 0, 0
        for a, b in ((0, 32), (1, 32), (32, 1), (32, 32), (0xffffffff, 1), (1, 0x80000000)):
            for c in (2, 0xffffffff):
                yield "cfg", a, b, c, 0, 0
        for a in range(32):
            for b in range(32):
                for flags in (0, 1, 2, 3):
                    cfg = (a << 24) | (b << 16) | flags | 0xe0e0fffc
                    for ofl in (0, 1, 0x80000000, 0xffffffff):
                        yield "dump", 0, 0, 0, cfg, ofl

    counts = Counter()
    samples = {}
    vectors = out / "arm-fixtures.txt"
    trace_path = out / "exact-traces.txt.gz"
    with vectors.open("w") as stream, gzip.open(trace_path, "wt", compresslevel=6) as exact:
        for name, a, b, c, cfg, ofl in inputs():
            state.update(events=0, hash=14695981039346656037, sample=[], trace=[])
            for reg, value in ((UC_ARM_REG_R0, a), (UC_ARM_REG_R1, b), (UC_ARM_REG_R2, c),
                               (UC_ARM_REG_R3, 0x55555555), (UC_ARM_REG_SP, 0x1000f000), (UC_ARM_REG_LR, 0x20000000)):
                u.reg_write(reg, value)
            u.mem_write(0xc4000200, struct.pack("<I", cfg))
            u.mem_write(0xc400020c, struct.pack("<I", ofl))
            u.emu_start(RANGES[name][0], 0x20000000, timeout=2000000, count=20000)
            assert u.reg_read(UC_ARM_REG_PC) == 0x20000000
            result = u.reg_read(UC_ARM_REG_R0)
            stream.write(f'{name} {a} {b} {c} {cfg} {ofl} {result} {state["events"]} {state["hash"]}\n')
            exact.write(f'CASE {name} {a} {b} {c} {cfg} {ofl} {result} {state["events"]}\n')
            exact.write("\n".join(state["trace"]) + "\nEND\n")
            counts[name] += 1
            sample_key = f'{name}-{"success" if result == 0 else "error"}'
            if sample_key not in samples or (name == "dump" and cfg & 1 and sample_key+"-enabled" not in samples):
                if name == "dump" and cfg & 1: sample_key += "-enabled"
                samples[sample_key] = dict(inputs=[a,b,c,cfg,ofl], result=result, event_count=state["events"], events=state["sample"], truncated=state["events"]>40)
            if sum(counts.values()) % 1000 == 0:
                print(dict(counts), flush=True)
    reviewed = {}
    for name, (start, code_end, pool_end) in RANGES.items():
        reviewed[name] = dict(registration_label="mix."+name, original_mangled_name=None,
            runtime_entry=start, image_file_offset=start-0x1f0,
            reviewed_code_end_exclusive=code_end, literal_pool_end_exclusive=pool_end,
            reviewed_code_sha256=hashlib.sha256(image[start-0x1f0:code_end-0x1f0]).hexdigest(),
            literal_pool_sha256=hashlib.sha256(image[code_end-0x1f0:pool_end-0x1f0]).hexdigest(),
            extent_basis="Contiguous ARM body, branch targets and terminal returns reviewed; separate adjacent literal pool. Not ELF symbol sizes.")
    proof = dict(image_sha256=IMAGE_SHA, unicorn_version=unicorn.__version__, counts=dict(counts),
                 fixture_sha256=hashlib.sha256(vectors.read_bytes()).hexdigest(),
                 exact_trace_sha256=hashlib.sha256(trace_path.read_bytes()).hexdigest(),
                 trace_comparison="Complete ordered event records preserved as gzip text; C++ replay must compare every event exactly. FNV1a64 retained as an additional summary only.",
                 external_hook_contract="0x17f30 diagnostic(code,line,file) and 0x180c8 printf: record calls and return normally; no scheduler/RTOS or device behavior modeled.",
                 register_model="RAM-backed addresses0xc4000200/204/20c; writes and reads logged in order. No real MMIO.",
                 callbacks=reviewed, original_basic_blocks_exercised=[hex(x) for x in sorted(blocks)], hooks=dict(hook_counts),
                 hardware_verified=False, original_arm_abi_compatible=False,
                 tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (out / "arm-oracle.json").write_text(json.dumps(proof, indent=2)+"\n")
    (out / "representative-traces.json").write_text(json.dumps(samples, indent=2)+"\n")
    print("COMPLETE", out, dict(counts), flush=True)


if __name__ == "__main__":
    main()
