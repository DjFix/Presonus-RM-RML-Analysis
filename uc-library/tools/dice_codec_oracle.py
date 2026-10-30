#!/usr/bin/env python3
"""Run original global DICE packing helpers in isolated ARM memory."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import arm_const as arm

NAMES={"P":"pack32(unsigned int, unsigned char*)","U":"unpack32(unsigned char const*)",
       "p":"pack16(unsigned short, unsigned char*)","u":"unpack16(unsigned char const*)"}


def sha(data):return hashlib.sha256(data).hexdigest()


def cases(operations):
    rng=random.Random(0x53595845)
    if "P" in operations:
        for n in range(65536):yield "P",n,b""
        for n in range(65536):yield "P",n<<16,b""
        for n in range(32):
            yield "P",1<<n,b"";yield "P",0xffffffff^(1<<n),b""
        for _ in range(4096):yield "P",rng.getrandbits(32),b""
    if "U" in operations:
        for fill in (0,0x7f,0x80,0xff,0x55,0xaa):
            for position in range(5):
                for n in range(256):
                    data=bytearray([fill]*5);data[position]=n;yield "U",0,bytes(data)
        for n in range(65536):yield "U",0,bytes([0xa5,n>>8,n&255,0xa5,0xa5])
        for _ in range(4096):yield "U",0,bytes(rng.getrandbits(8) for _ in range(5))
    if "p" in operations:
        for n in range(65536):yield "p",n,b""
    if "u" in operations:
        for n in range(65536):yield "u",0,bytes([n>>9,(n>>2)&127,n&3])
        for n in range(65536):yield "u",0,bytes([n>>8,n&255,0xfc|(((n>>8)^n)&3)])
        for first,second in ((0,255),(255,0),(255,255),(128,128)):
            for last in range(256):yield "u",0,bytes([first,second,last])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("repository",type=Path);a=p.parse_args()
    lib=a.repository.resolve()/"uc-library"
    out=lib/"validation/dice-codec/runs"/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out.mkdir(parents=True,exist_ok=False)
    for role in ("client","server"):
        directory=lib/"recovered-all"/role;manifest=json.loads((directory/"manifest.json").read_text())
        binary=a.repository/manifest["path"];raw=binary.read_bytes();assert sha(raw)==manifest["sha256"]
        symbols=json.loads((directory/"symbols.json").read_text())
        functions={op:next(s for s in symbols if s["kind"]=="STT_FUNC" and s["demangled"]==name) for op,name in NAMES.items() if any(s["kind"]=="STT_FUNC" and s["demangled"]==name for s in symbols)}
        for s in functions.values():
            code=(directory/s["export_path"]).read_bytes()
            assert code==raw[s["file_offset"]:s["file_offset"]+s["size"]] and sha(code)==s["sha256"]
        u=unicorn.Uc(unicorn.UC_ARCH_ARM,unicorn.UC_MODE_ARM);pages=set();elf_ranges=[]
        with binary.open("rb") as stream:
            for seg in ELFFile(stream).iter_segments():
                if seg["p_type"]!="PT_LOAD":continue
                start=int(seg["p_vaddr"]);end=start+int(seg["p_memsz"])
                for page in range(start&~4095,(end+4095)&~4095,4096):
                    if page not in pages:u.mem_map(page,4096);pages.add(page)
                u.mem_write(start,seg.data());elf_ranges.append((start,end))
        buffer=0x10000000;stack=0x20000000;stop=0x30000000
        u.mem_map(buffer,4096);u.mem_map(stack,65536);u.mem_map(stop,4096)
        state={};blocks=set()

        def memory(uc,access,address,size,value,user):
            allowed=elf_ranges+[(state["pointer"],state["pointer"]+state["width"]),(stack,stack+65536)]
            assert any(lo<=address and address+size<=hi for lo,hi in allowed),hex(address)
            if state["pointer"]<=address<state["pointer"]+state["width"]:
                assert size==1
                state["writes" if access==unicorn.UC_MEM_WRITE else "reads"].append(address-state["pointer"])

        def block(uc,address,size,user):
            assert any(s["address"]<=address<s["address"]+s["size"] for s in functions.values()),hex(address)
            blocks.add(address)
        u.hook_add(unicorn.UC_HOOK_MEM_READ|unicorn.UC_HOOK_MEM_WRITE,memory)
        u.hook_add(unicorn.UC_HOOK_BLOCK,block)
        role_out=out/role;role_out.mkdir();path=role_out/"arm-vectors.txt"
        counts=Counter();orders={};pack_returns={}
        with path.open("w") as stream:
            for index,(op,value,data) in enumerate(cases(functions)):
                offset=1+index%7;width=5 if op in ("P","U") else 3
                before=bytearray([0xa5]*32)
                if data:before[offset:offset+width]=data
                u.mem_write(buffer,bytes(before))
                state.update(pointer=buffer+offset,width=width,writes=[],reads=[])
                u.reg_write(arm.UC_ARM_REG_CPSR,0x10)
                for i in range(13):u.reg_write(getattr(arm,f"UC_ARM_REG_R{i}"),0)
                u.reg_write(arm.UC_ARM_REG_R0,value if op in ("P","p") else buffer+offset)
                u.reg_write(arm.UC_ARM_REG_R1,buffer+offset)
                u.reg_write(arm.UC_ARM_REG_SP,stack+0xff00);u.reg_write(arm.UC_ARM_REG_LR,stop)
                u.emu_start(functions[op]["address"],stop,count=2000)
                assert u.reg_read(arm.UC_ARM_REG_PC)==stop and u.reg_read(arm.UC_ARM_REG_SP)==stack+0xff00
                after=bytes(u.mem_read(buffer,32));returned=u.reg_read(arm.UC_ARM_REG_R0)
                order={"reads":state["reads"],"writes":state["writes"]}
                if op not in orders:orders[op]=order
                assert orders[op]==order
                if op in ("P","p"):
                    pack_returns.setdefault(op,set()).add(returned)
                    assert state["writes"]==([0,1,2,4,3] if op=="P" else [2,0,1])
                    assert after[:offset]==before[:offset] and after[offset+width:]==before[offset+width:]
                    returned=0  # Original packer return contract is unresolved.
                else:
                    assert after==before and not state["writes"]
                stream.write(f'{op} {value:08x} {offset:x} {before.hex()} {returned:08x} {after.hex()}\n')
                counts[op]+=1
                if index%50000==0:print(role,index,dict(counts),flush=True)
        report=dict(role=role,original_elf_sha256=manifest["sha256"],functions=functions,cases=dict(counts),
            fixture_sha256=sha(path.read_bytes()),oracle="Only original global integer packing/unpacking ARM instructions; no hooks or Core code",
            unicorn_version=unicorn.__version__,ordinary_ram_access_order=orders,
            pack_incidental_r0_words={op:sorted(values) for op,values in pack_returns.items()},
            pack_return_caveat="Original void-vs-value declaration unresolved; C++ output-only packers are declaration-pending. Fixtures deliberately exclude pack return comparisons.",
            method_blocks={op:[hex(x) for x in sorted(blocks) if s["address"]<=x<s["address"]+s["size"]] for op,s in functions.items()},
            domain="32bitpack low/high16bit sweeps+walkingbits+4096randomwords;32bitunpack eachbyte0..255 insixfillcontexts,65536adjacentbytepairs+4096random5bytevectors. Server16bitpack exhaustive65536 values;16bitunpack allcanonicalvalues+65536noncanonicalfirstbytepairs+1024finalbytecases. Buffer offsets1..7,exact32bytebuffercomparisons; no volatile/MMIO/orderABI claim. No hardware or pointerownership claim.",
            tool_sha256=sha(Path(__file__).read_bytes()))
        (role_out/"arm-oracle.json").write_text(json.dumps(report,indent=2)+"\n")
        print("COMPLETE",role,dict(counts),flush=True)
    print("OUTPUT",out,flush=True)


if __name__=="__main__":main()
