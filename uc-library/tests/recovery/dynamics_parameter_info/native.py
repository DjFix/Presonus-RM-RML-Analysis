"""Independent ELF-byte oracle; never reads the C++ implementation."""
import hashlib, io, json, struct, subprocess
from pathlib import Path
from elftools.elf.elffile import ELFFile
CONTRACT = "temp/recovery-work/rolling-c001-20261124/selection/continuation-intake-20261126/DYNAMICS_DATA_SUPPORT_CONTRACT.json"
def digest(b): return hashlib.sha256(b).hexdigest()
def collect(root):
    context = json.loads((root / "temp/recovery-work/dynamics-data-support-sol61/CONTEXT.json").read_text())
    assert digest((root / "temp/recovery-work/dynamics-data-support-sol61/CONTEXT.json").read_bytes()) == "7fee9cb5c9f966323ca8bbbd8dba775e9b029cc91a74b33e239352efb9944091"
    for path, sha in context["read_files"].items():
        assert digest((root/path).read_bytes()) == sha, path
    contract = json.loads((root/CONTRACT).read_text())
    result=[]
    for identity in contract["data_identities"]:
        data=(root/identity["elf_path"]).read_bytes()
        assert digest(data)==identity["elf"]
        elf=ELFFile(io.BytesIO(data)); sec=elf.get_section(identity["section"])
        assert sec.name==identity["section_name"]
        offset=sec["sh_offset"]+identity["address"]-sec["sh_addr"]
        assert offset==identity["file_offset"]
        matches=[sym for sym in elf.get_section_by_name(".symtab").iter_symbols() if sym.name==identity["symbol"] and sym["st_value"]==identity["address"] and sym["st_size"]==identity["size"] and sym["st_shndx"]==identity["section"] and sym["st_info"]["type"]=="STT_OBJECT"]
        assert len(matches)==1
        assert matches[0]["st_info"]["bind"]==identity["binding"]
        raw=data[offset:offset+identity["size"]]; assert digest(raw)==identity["range_sha256"]
        strings=[]
        def text(addr):
            if not addr: return None
            sections=[s for s in elf.iter_sections() if s["sh_type"]!="SHT_NOBITS" and s["sh_addr"]<=addr<s["sh_addr"]+s["sh_size"] and s["sh_flags"]&2]
            assert len(sections)==1
            s=sections[0]; off=s["sh_offset"]+addr-s["sh_addr"]; end=data.index(b"\0",off,s["sh_offset"]+s["sh_size"])
            b=data[off:end+1]; strings.append(dict(address=addr,file_offset=off,bytes=b.hex(),sha256=digest(b)))
            return b[:-1].decode("ascii")
        entries=[]
        for i in range(10):
            row=raw[i*84:(i+1)*84]; words=struct.unpack("<21I",row)
            texts={k:text(words[j]) for k,j in zip(["unit","curve","labels","title","short_title"],range(16,21))}
            assert texts["labels"] is None
            entries.append(dict(type=words[0],tag=words[1],name=row[8:40].split(b"\0")[0].decode(),name_bytes=row[8:40].hex(),float_bits=[f"{w:08x}" for w in words[10:15]],flags=words[15],pointers=dict(zip(["unit","curve","labels","title","short_title"],words[16:21])),texts=texts))
        for got,want in zip(entries,identity["decoded_entries"]):
            for key in ["type","tag","name","float_bits","flags","pointers","texts"]: assert got[key]==want[key], (identity["address"],key)
        result.append(dict(identity={k:v for k,v in identity.items() if k!="decoded_entries"},demangled=subprocess.check_output(["/usr/bin/c++filt",identity["symbol"]],text=True).strip(),entries=entries,strings=strings))
    def normalized(x): return [{k:v for k,v in e.items() if k!="pointers"} for e in x["entries"]]
    for component in ["GateComponent","CompressorComponent"]:
        group=[x for x in result if x["identity"]["component"]==component]
        assert len(group)==3 and all(normalized(x)==normalized(group[0]) for x in group)
    return dict(kind="original_object_byte_fixtures",function_credit=0,objects=result)
if __name__=="__main__":
    root=Path(__file__).resolve().parents[4]
    print(json.dumps(collect(root),indent=2))
