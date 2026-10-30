#!/usr/bin/env python3
"""Execute bounded original Core linear methods and original ARM float helpers."""
import argparse
import collections
import hashlib
import json
import random
import struct
from datetime import datetime, timezone
from pathlib import Path

from mixer_dsp_oracle import Oracle
import unicorn

PREFIXES = {
    "N":"Core::LinearInterpolator::normalizedToRange(",
    "R":"Core::LinearInterpolator::rangeToNormalized(",
    "V":"Core::LinearReverseInterpolator::normalizedToRange(",
    "W":"Core::LinearReverseInterpolator::rangeToNormalized(",
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("repository", type=Path)
    a = p.parse_args()
    lib = a.repository.resolve() / "uc-library"
    out = lib / "validation/core-interpolator/runs" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out.mkdir(parents=True, exist_ok=False)
    edges = [0,0x80000000,1,0x80000001,0x007fffff,0x807fffff,0x00800000,0x80800000,
             0x3f000000,0xbf000000,0x3f800000,0xbf800000,0x40000000,0xc0000000,
             0x7f7fffff,0xff7fffff,0x7f800000,0xff800000,0x7fc12345,0xffc12345,
             0x7fa12345,0xffa12345,0x7fffffff,0xffffffff]
    rng = random.Random(0x434f5245)
    triples = [(lo,hi,x) for lo in edges for hi in edges for x in edges]
    triples += [tuple(rng.getrandbits(32) for _ in range(3)) for _ in range(4096)]
    for role in ("client", "server"):
        directory = lib / "recovered-all" / role
        oracle = Oracle(a.repository.resolve(), role)
        symbols = json.loads((directory / "symbols.json").read_text())
        oracle.functions = {op:next(s for s in symbols if s["kind"] == "STT_FUNC" and s["demangled"].startswith(prefix)) for op,prefix in PREFIXES.items()}
        binary = (a.repository / oracle.manifest["path"]).read_bytes()
        for s in oracle.functions.values():
            raw = (directory / s["export_path"]).read_bytes()
            assert raw == binary[s["file_offset"]:s["file_offset"]+s["size"]]
            assert hashlib.sha256(raw).hexdigest() == s["sha256"]
        role_out = out / role
        role_out.mkdir()
        counts = collections.Counter()
        path = role_out / "arm-vectors.txt"
        with path.open("w") as stream:
            for i,(lo,hi,x) in enumerate(triples):
                storage = struct.pack("<II",lo,hi) + bytes(range(28))
                for op in PREFIXES:
                    returned,after = oracle.call(op,storage,[x])
                    assert after == storage, "original method unexpectedly mutated object"
                    counts[op] += 1
                    stream.write(f'{op} {lo:08x} {hi:08x} {x:08x} {returned:08x}\n')
                if i % 2000 == 0:
                    print(role,i,dict(counts),flush=True)
        helper_names = {"__aeabi_fsub","__aeabi_fadd","__aeabi_fmul","__aeabi_fdiv","__aeabi_fcmple","__aeabi_fcmplt","__aeabi_fcmpgt"}
        helpers = [s for s in symbols if s["kind"] == "STT_FUNC" and s["mangled"] in helper_names]
        for s in helpers:
            raw = (directory/s["export_path"]).read_bytes()
            assert raw == binary[s["file_offset"]:s["file_offset"]+s["size"]]
            assert hashlib.sha256(raw).hexdigest() == s["sha256"]
        report = dict(role=role,original_elf_sha256=oracle.manifest["sha256"], functions=oracle.functions,
            original_helpers=helpers,oracle="Original ARM methods and original ELF soft-float helper instructions; no arithmetic hooks",
            unicorn_version=unicorn.__version__,cases=dict(counts),fixture_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            fixture_domain="24 edge binary32 words cubed across minimum,maximum,input; 4096 deterministic random bit-pattern triples, each executed for all four methods. Original 36-byte object region unchanged.",
            edge_words=[f"0x{x:08x}" for x in edges],random_seed="0x434f5245",random_triples=4096,
            method_blocks={op:[hex(x) for x in sorted(oracle.blocks) if s["address"]<=x<s["address"]+s["size"]] for op,s in oracle.functions.items()},
            dependencies={"tools/mixer_dsp_oracle.py":hashlib.sha256((lib/"tools/mixer_dsp_oracle.py").read_bytes()).hexdigest(),
                          "tools/core_interpolator_oracle.py":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
        (role_out/"arm-oracle.json").write_text(json.dumps(report,indent=2)+"\n")
        print("COMPLETE",role,dict(counts),flush=True)
    print("OUTPUT",out,flush=True)


if __name__ == "__main__":
    main()
