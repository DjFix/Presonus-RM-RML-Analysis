#!/usr/bin/env python3
"""Execute only original PreSonus integer mixer-state methods; no Core code."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import struct
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import arm_const as arm

NAMES = {
"S":"Presonus::MixerClientComponentBase::isStereoChannelType(Presonus::ChannelType) const",
"A":"Presonus::MixerClientComponent::isAggregateMeteringChannelType(Presonus::ChannelType) const",
"G":"Presonus::MixerClientComponentBase::getNumGeqs() const",
"M":"Presonus::MixerClientComponentBase::getNumMixGeqs() const",
"C":"Presonus::MixerClientComponentBase::getCascadeState() const",
"P":"Presonus::MixerClientComponentBase::getMasterMixer() const",
"Q":"Presonus::MixerClientComponentBase::getSlaveMixer() const",
}


def sha(data): return hashlib.sha256(data).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("repository",type=Path);a=p.parse_args()
    lib=a.repository.resolve()/"uc-library"
    out=lib/"validation/mixer-state/runs"/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out.mkdir(parents=True,exist_ok=False)
    rng=random.Random(0x4d495845)
    enum_words=list(range(65536))+[0x7fffffff,0x80000000,0xffff0000,0xffffff80,0xffffffff]+[rng.getrandbits(32) for _ in range(4096)]
    count_words=[0,1,2,3,4,7,8,15,16,0x7ffffffe,0x7fffffff,0x80000000,0x80000001,0xfffffffe,0xffffffff]+[rng.getrandbits(32) for _ in range(1024)]
    links=[0,1,4,0x10000000,0x7fffffff,0x80000000,0xffffffff]
    for role in ("client","server"):
        directory=lib/"recovered-all"/role
        manifest=json.loads((directory/"manifest.json").read_text())
        binary=a.repository/manifest["path"]
        raw=binary.read_bytes();assert sha(raw)==manifest["sha256"]
        symbols=json.loads((directory/"symbols.json").read_text())
        functions={op:next(s for s in symbols if s["kind"]=="STT_FUNC" and s["demangled"]==name) for op,name in NAMES.items()}
        for s in functions.values():
            code=(directory/s["export_path"]).read_bytes()
            assert code==raw[s["file_offset"]:s["file_offset"]+s["size"]] and sha(code)==s["sha256"]
        table=next(s for s in symbols if s["demangled"]=="vtable for Presonus::MixerClientComponentBase")
        data=(directory/table["export_path"]).read_bytes()
        assert data==raw[table["file_offset"]:table["file_offset"]+table["size"]] and sha(data)==table["sha256"]
        assert struct.unpack_from("<I",data,0x4c)[0]==functions["G"]["address"]
        u=unicorn.Uc(unicorn.UC_ARCH_ARM,unicorn.UC_MODE_ARM)
        pages=set();elf_ranges=[]
        with binary.open("rb") as stream:
            elf=ELFFile(stream)
            for segment in elf.iter_segments():
                if segment["p_type"]!="PT_LOAD":continue
                start=int(segment["p_vaddr"]);end=start+int(segment["p_memsz"])
                for page in range(start&~4095,(end+4095)&~4095,4096):
                    if page not in pages:u.mem_map(page,4096);pages.add(page)
                u.mem_write(start,segment.data());elf_ranges.append((start,end))
        obj=0x10000000;configuration=0x10001000;fake_vtable=0x10002000;stack=0x20000000;stop=0x30000000;override_pc=0x30001000
        u.mem_map(obj,0x3000);u.mem_map(stack,0x10000);u.mem_map(stop,0x2000)
        u.mem_write(fake_vtable+0x44,struct.pack("<I",override_pc))
        state={};blocks=set()

        def override(uc,address,size,user):
            assert uc.reg_read(arm.UC_ARM_REG_R0)==obj
            state["calls"]+=1
            uc.reg_write(arm.UC_ARM_REG_R0,state["override"])
            uc.reg_write(arm.UC_ARM_REG_PC,uc.reg_read(arm.UC_ARM_REG_LR))

        def block(uc,address,size,user):
            assert address==override_pc or any(s["address"]<=address<s["address"]+s["size"] for s in functions.values()),f"unapproved code {address:#x}"
            blocks.add(address)

        def memory(uc,access,address,size,value,user):
            allowed=elf_ranges+[(obj,obj+0x688),(configuration,configuration+0x100),(fake_vtable,fake_vtable+0x100),(stack,stack+0x10000)]
            assert any(start<=address and address+size<=end for start,end in allowed),f"unexpected memory {address:#x}"
        u.hook_add(unicorn.UC_HOOK_CODE,override,begin=override_pc,end=override_pc)
        u.hook_add(unicorn.UC_HOOK_BLOCK,block)
        u.hook_add(unicorn.UC_HOOK_MEM_READ|unicorn.UC_HOOK_MEM_WRITE,memory)
        role_out=out/role;role_out.mkdir();counts=Counter();pending=Counter()

        def call(op,channel=0,present=0,count=0,master=0,slave=0,overridden=0):
            storage=bytearray(b"\xa5"*0x688)
            struct.pack_into("<I",storage,0,fake_vtable if op=="O" else table["address"]+8)
            struct.pack_into("<III",storage,0x678,master,slave,0xa5a5a5a5)
            struct.pack_into("<I",storage,0x684,configuration if present else 0)
            config=bytearray(b"\x5a"*0x100);struct.pack_into("<I",config,0x5c,count)
            u.mem_write(obj,bytes(storage));u.mem_write(configuration,bytes(config))
            state.update(calls=0,override=overridden)
            u.reg_write(arm.UC_ARM_REG_CPSR,0x10)
            for i in range(13):u.reg_write(getattr(arm,f"UC_ARM_REG_R{i}"),0)
            u.reg_write(arm.UC_ARM_REG_R0,obj);u.reg_write(arm.UC_ARM_REG_R1,channel)
            u.reg_write(arm.UC_ARM_REG_SP,stack+0xff00);u.reg_write(arm.UC_ARM_REG_LR,stop)
            function=functions["M" if op=="O" else op]
            u.emu_start(function["address"],stop,count=2000)
            assert u.reg_read(arm.UC_ARM_REG_PC)==stop and u.reg_read(arm.UC_ARM_REG_SP)==stack+0xff00
            assert bytes(u.mem_read(obj,len(storage)))==storage and bytes(u.mem_read(configuration,len(config)))==config
            assert state["calls"]==(1 if op=="O" else 0)
            return u.reg_read(arm.UC_ARM_REG_R0),state["calls"]

        path=role_out/"arm-vectors.txt"
        with path.open("w") as stream:
            def emit(op,channel=0,present=0,count=0,master=0,slave=0,overridden=0):
                result,calls=call(op,channel,present,count,master,slave,overridden)
                stream.write(f'{op} {channel:08x} {present:08x} {count:08x} {master:08x} {slave:08x} {overridden:08x} {result:08x} {calls:x}\n')
                counts[op]+=1
            for channel in enum_words:
                emit("S",channel);emit("A",channel)
            for count in count_words:
                for present in (0,1):
                    emit("G",present=present,count=count);emit("M",present=present,count=count)
                    emit("O",present=present,count=count,overridden=count)
            for master in links:
                for slave in links:emit("C",master=master,slave=slave)
            for _ in range(1024):emit("C",master=rng.getrandbits(32),slave=rng.getrandbits(32))
        pending_path=role_out/"declaration-pending-pointer-vectors.txt"
        with pending_path.open("w") as stream:
            for master in links:
                for slave in links:
                    for op in ("P","Q"):
                        result,calls=call(op,master=master,slave=slave)
                        assert result==(master if op=="P" else slave)
                        stream.write(f'{op} {master:08x} {slave:08x} {result:08x}\n');pending[op]+=1
        report=dict(role=role,original_elf_sha256=manifest["sha256"],functions=functions,vtable=table,
            virtual_dispatch_evidence="Originalvptr+0x44 is originalvtable+0x4c, which points to getNumGeqs. Base dispatch executes original method; overridefixture executes a singleexplicitgetNumGeqs return-word hook.",
            original_field_offsets={"master_word":"0x678","slave_word":"0x67c","configuration_pointer":"0x684","configuration_geq_word":"0x5c"},
            oracle="Only original Presonus integer methods; no Core functions or floating helpers executed",unicorn_version=unicorn.__version__,
            cases=dict(counts),fixture_sha256=sha(path.read_bytes()),pending_pointer_cases=dict(pending),pending_pointer_fixture_sha256=sha(pending_path.read_bytes()),
            method_blocks={op:[hex(x) for x in sorted(blocks) if s["address"]<=x<s["address"]+s["size"]] for op,s in functions.items()},
            domain="Channel words0..65535 plus5boundary+4096random32bit values; GEQnull/non-null configuration with15edge+1024randomcount words; virtualoverride returns samefull32bit domain and records onecallwithoriginalthis; cascade7x7linkwords+1024randompairs. Original0x688-byte object and0x100-byte configuration unchanged. Valid nonoverlapping modeledmemory; no hardware or binaryABI claim.",
            tool_sha256=sha(Path(__file__).read_bytes()))
        (role_out/"arm-oracle.json").write_text(json.dumps(report,indent=2)+"\n")
        print("COMPLETE",role,dict(counts),flush=True)
    print("OUTPUT",out,flush=True)


if __name__=="__main__":main()
