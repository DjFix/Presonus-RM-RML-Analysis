"""Re-execute the sealed ARM oracle and compare the selected variant fixture."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from elftools.elf.elffile import ELFFile

here = Path(__file__).resolve().parent
observations = json.loads(subprocess.check_output([sys.executable, sys.argv[1]]))
fixture = json.loads((here / "fixtures.json").read_text())
original = fixture["original"]
binary = Path(original["elf_path"])
elf_bytes = binary.read_bytes()
if hashlib.sha256(elf_bytes).hexdigest() != original["elf"]:
    raise SystemExit("Original ELF SHA-256 mismatch")
with binary.open("rb") as stream:
    section = ELFFile(stream).get_section(original["section"])
    delta = original["address"] - section["sh_addr"]
    offset = section["sh_offset"] + delta
    body = elf_bytes[offset:offset + original["size"]]
    if (section.name != original["section_name"]
            or offset != original["file_offset"] or delta < 0
            or delta + len(body) > section["sh_size"]
            or body.hex() != original["range_hex"]
            or hashlib.sha256(body).hexdigest() != original["range_sha256"]):
        raise SystemExit("Original ELF section/range mismatch")
cases = [case for case in observations["cases"]
         if case["mangled"] == fixture["original"]["mangled"]]
if cases != fixture["cases"] or len(cases) != 16:
    raise SystemExit("Native constructor observations differ from the sealed fixture")
print(f"PASS {len(cases)} ARM constructor observations")
