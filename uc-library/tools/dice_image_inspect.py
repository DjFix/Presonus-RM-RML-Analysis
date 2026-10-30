#!/usr/bin/env python3
"""Offline, nonexecuting inspection of the embedded DICE surface image."""
import argparse
import hashlib
import json
import re
import struct
from datetime import datetime, timezone
from pathlib import Path

import capstone
from pypdf import PdfReader


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path)
    args = parser.parse_args()
    root = args.repository.resolve()
    lib = root / "uc-library"
    out = lib / "validation/dice-image" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out.mkdir(parents=True, exist_ok=False)
    symbols = json.loads((lib / "recovered-dice/client/symbols.json").read_text())
    symbol = next(s for s in symbols if s["mangled"] == "_ZL18dice3_surface_code")
    image_path = lib / "recovered-dice/client" / symbol["export_path"]
    data = image_path.read_bytes()
    assert sha(image_path) == symbol["sha256"] and len(data) == symbol["size"]
    strings = [{"file_offset":m.start(), "text":m.group().decode("ascii")} for m in re.finditer(rb"[\x20-\x7e]{4,}", data)]
    (out / "strings.json").write_text(json.dumps(strings, indent=2) + "\n")
    (out / "strings.txt").write_text("".join(f'{s["file_offset"]:08x} {s["text"]}\n' for s in strings))
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM | capstone.CS_MODE_LITTLE_ENDIAN)
    # File offset 0x10 provisionally corresponds to vector address zero; this
    # rendering labels offsets only, so it does not assert a runtime mapping.
    lines = [f'{i.address:08x} {i.bytes.hex():8} {i.mnemonic} {i.op_str}' for i in md.disasm(data[0x10:0x350], 0x10)]
    (out / "startup-file-offsets.arm.txt").write_text("\n".join(lines) + "\n")
    header_words = [f"0x{x:08x}" for x in struct.unpack_from("<16I", data)]
    load = struct.unpack_from("<I", data, 8)[0]
    word_count = int.from_bytes(data[12:15], "little")
    delta = load - 16

    def cstring(address):
        offset = address - delta
        if not 16 <= offset < len(data):
            return None
        end = data.find(b"\0", offset, min(len(data), offset + 4096))
        if end < 0 or any(b not in (9, 10, 13) and not 32 <= b <= 126 for b in data[offset:end]):
            return None
        return data[offset:end].decode("ascii")

    records = []
    callback_lines = []
    for hit in re.finditer(b"loot", data):
        offset = hit.start() - 12
        if offset < 16 or offset % 4:
            continue
        pairs = []
        for cursor in range(offset, min(offset + 256, len(data) - 7), 8):
            tag, value = struct.unpack_from("<II", data, cursor)
            pairs.append((tag, value))
            if tag == 0xffffffff:
                break
        fields = dict(pairs)
        if fields.get(2) != 0x746f6f6c or not {1, 3, 8, 11, 0xffffffff} <= fields.keys():
            continue
        callback = fields[3]
        callback_offset = (callback & ~1) - delta
        record = {"descriptor_file_offset":offset, "descriptor_runtime_address":offset + delta,
                  "raw_tag_value_pairs":pairs, "name":cstring(fields[1]), "context":cstring(fields[12]) if 12 in fields else None,
                  "usage":cstring(fields[8]), "argument_pattern":cstring(fields[9]) if 9 in fields else None,
                  "constants":cstring(fields[10]) if 10 in fields else None, "description":cstring(fields[11]),
                  "callback_runtime_address":callback, "callback_file_offset":callback_offset,
                  "callback_mode":"Thumb" if callback & 1 else "ARM",
                  "original_c_cpp_symbol":None, "function_extent_verified":False}
        records.append(record)
        callback_lines.append(f'\n# {record["context"]}.{record["name"]}: stored callback 0x{callback:x}, file offset 0x{callback_offset:x}; extent unknown')
        decoder = capstone.Cs(capstone.CS_ARCH_ARM, (capstone.CS_MODE_THUMB if callback & 1 else capstone.CS_MODE_ARM) | capstone.CS_MODE_LITTLE_ENDIAN)
        for instruction in decoder.disasm(data[callback_offset:callback_offset+96], callback & ~1):
            callback_lines.append(f'{instruction.address:08x} {instruction.bytes.hex():8} {instruction.mnemonic} {instruction.op_str}')
    (out / "cli-registration-table.json").write_text(json.dumps(records, indent=2) + "\n")
    (out / "cli-callback-prefixes.arm.txt").write_text("\n".join(callback_lines) + "\n")
    payload = data[16:16+word_count*4]
    crc_results = {}
    for initial in (0, 0xffffffff):
        crc = initial
        for byte in payload:
            crc ^= byte << 24
            for _ in range(8):
                crc = ((crc << 1) ^ (0x04c11db7 if crc & 0x80000000 else 0)) & 0xffffffff
        crc_results[f"initial_0x{initial:08x}"] = f"0x{crc:08x}"
    docs = []
    for name in ("DICE_III_Boot.pdf", "DICE_III_User_Guide_MemoryMap.pdf", "TCD30xx - Firmware Development.pdf", "Digital IO and Networking Engine Hardware Guide.pdf"):
        path = root / "doc/DICE_III_User_Guide" / name
        reader = PdfReader(path)
        text = "\n".join(f'\n=== PDF PAGE {n+1} ===\n' + (page.extract_text() or "") for n, page in enumerate(reader.pages))
        target = out / (name + ".txt")
        target.write_text(text)
        docs.append({"path":str(path.relative_to(root)), "sha256":sha(path), "pages":len(reader.pages), "text":target.name})
    component = root / "components/dice3-surface-bin"
    proof = {"analysis":"raw image inspection only; no firmware execution or C++ recovery", "image_symbol":symbol,
             "original_elf_sha256":"304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0",
             "image_header_le_words":header_words, "has_elf_magic":data.startswith(b"\x7fELF"),
             "decoded_boot_header":{"signature":data[:4].decode("ascii"), "family":data[4], "flags":data[5],
                 "pll_multiplier":data[6], "pll_predivider":data[7], "load_address":load,
                 "payload_word_count":word_count, "payload_bytes":word_count*4, "spi_baud_divider":data[15],
                 "payload_exactly_fills_image":len(payload)==word_count*4 and len(data)==16+word_count*4},
             "runtime_address_mapping":{"formula":"runtime = file_offset + load_address - 16", "delta":delta,
                 "evidence":"Boot header load field plus literal pointers to CLI names, contexts and usage strings"},
             "crc32_msb_polynomial_0x04c11db7_no_final_xor":crc_results,
             "cli_descriptor_count":len(records), "unique_registered_callbacks":len({r["callback_runtime_address"] for r in records}),
             "component":{"path":str(component.relative_to(root)), "sha256":sha(component), "same_as_embedded":component.read_bytes()==data},
             "docs":docs, "capstone_version":capstone.__version__, "tool_sha256":sha(Path(__file__))}
    (out / "inspection.json").write_text(json.dumps(proof, indent=2) + "\n")
    print(out)
    print(json.dumps({"header":header_words[:4],"size":len(data),"sha256":sha(image_path),"strings":len(strings),"same_component":proof["component"]["same_as_embedded"]}))


if __name__ == "__main__":
    main()
