#!/usr/bin/env python3
"""Inspect bounded original PreSonus metering methods, without decompiling Core."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM

NAMES = {
"Presonus::MeterMaid::setMeter(float)","Presonus::MeterMaid::setPeak(float)",
"Presonus::MeterMaid::setSignal(bool)","Presonus::MeterMaid::setClipped(bool)",
"Presonus::MeterMaid::isClipped() const", "Presonus::MeterBallistics::reset()",
"Presonus::MeterBallistics::setLevel(float)","Presonus::MeterBallistics::getPeakHold() const"}


def main(names_to_inspect=NAMES, group="metering"):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("repository",type=Path);a=p.parse_args()
    lib=a.repository.resolve()/"uc-library"
    out=lib/"validation"/group/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out.mkdir(parents=True,exist_ok=False)
    records=[]
    for role in ("client","server"):
        directory=lib/"recovered-all"/role
        manifest=json.loads((directory/"manifest.json").read_text())
        binary=(a.repository/manifest["path"]).read_bytes()
        assert hashlib.sha256(binary).hexdigest()==manifest["sha256"]
        symbols=json.loads((directory/"symbols.json").read_text())
        names={s["address"]:s["demangled"] for s in symbols if s["kind"]=="STT_FUNC"}
        for s in symbols:
            if s["kind"]!="STT_FUNC" or s["demangled"] not in names_to_inspect:continue
            code=(directory/s["export_path"]).read_bytes()
            assert code==binary[s["file_offset"]:s["file_offset"]+s["size"]]
            assert hashlib.sha256(code).hexdigest()==s["sha256"]
            lines=[s["demangled"],s["mangled"]]
            for i in Cs(CS_ARCH_ARM,CS_MODE_ARM).disasm(code,s["address"]):
                target=int(i.op_str[1:],16) if i.mnemonic in ("bl","b") and i.op_str.startswith("#0x") else None
                lines.append(f'{i.address:08x} {i.bytes.hex():8} {i.mnemonic} {i.op_str}'+(" ; "+names[target] if target in names else ""))
            name=f'{role}-{s["address"]:08x}.arm.txt'
            (out/name).write_text("\n".join(lines)+"\n")
            records.append(dict(s,role=role,original_elf_sha256=manifest["sha256"],disassembly=name))
    (out/"symbols.json").write_text(json.dumps(records,indent=2)+"\n")
    print(out)


if __name__=="__main__":main()
