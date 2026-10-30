"""Verify both local-name DSP ranges and retain application-only disassembly."""
import hashlib
import json
from pathlib import Path
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM

lib=Path("uc-library")
out=Path("evidence/recovery/2026-10-27/dsp-single-pole/inspection-01")
out.mkdir(parents=True,exist_ok=False)
root=lib/"recovered-all/server"
manifest=json.loads((root/"manifest.json").read_text())
binary=Path(manifest["path"])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(binary)==manifest["sha256"]
rows=[r for r in json.loads((root/"symbols.json").read_text()) if r["mangled"]=="_ZN3DSPL10SinglePoleEff" and r["size"]]
assert len(rows)==2
result=[]
binary_bytes=binary.read_bytes()
with binary.open("rb") as stream:
    elf=ELFFile(stream)
    for row in rows:
        sec=elf.get_section(row["section"])
        offset=sec["sh_offset"]+row["address"]-sec["sh_addr"]
        code=binary_bytes[offset:offset+row["size"]]
        assert len(code)==row["size"] and hashlib.sha256(code).hexdigest()==row["sha256"]
        assert code==(root/row["export_path"]).read_bytes()
        asm="\n".join(f"{i.address:08x} {i.mnemonic} {i.op_str}" for i in Cs(CS_ARCH_ARM,CS_MODE_ARM).disasm(code,row["address"]))
        (out/("{:08x}.arm.txt".format(row["address"]))).write_text(asm+"\n")
        result.append(dict(row,original_elf_sha256=manifest["sha256"],instructions=asm))
(out/"validation.json").write_text(json.dumps(dict(role="server",rows=result,tool_sha256=sha(Path(__file__)),scope="Original application code range inspection only; no readiness or hardware claim."),indent=2)+"\n")
for row in result:print(row["instructions"])
