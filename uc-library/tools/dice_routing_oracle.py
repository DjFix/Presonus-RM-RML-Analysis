#!/usr/bin/env python3
"""Execute original manager routing logic with an explicit setRoute boundary."""
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

NAMES={"P":"Presonus::DICE::Dice3Manager::setDiceRoutingProfile(Presonus::DICE::Dice3RoutingProfile)",
       "M":"Presonus::DICE::Dice3Manager::setDiceMonitorSource(int, int, int)"}
ROUTE="Presonus::DICE::Dice3Subsystem::setRoute(Presonus::DICE::Dice3AudioSinkDevice, Presonus::DICE::Dice3AudioSink, Presonus::DICE::Dice3AudioSourceDevice, Presonus::DICE::Dice3AudioSource)"


def sha(data):return hashlib.sha256(data).hexdigest()


def cases():
    rng=random.Random(0x44525445)
    profiles=list(range(65536))+[0x7fffffff,0x80000000,0xfffffffe,0xffffffff,0x80000001]+[rng.getrandbits(32) for _ in range(4096)]
    for i,profile in enumerate(profiles):yield "P",profile,0,0,[0,0xfffffffc,0xfffffff5,0x7fffffff],i&1
    patterns=[[0]*4,[0xfffffffc]*4,[0xfffffff5]*4,[0x80000000]*4,[0,0xfffffffc,0x7fffffff,0xdeadbeef]]
    for profile in (1,2,3):
        for returns in patterns:
            for swap in (0,1):yield "P",profile,0,0,returns,swap
    edges=[0,1,0xffffffff,15,16,0xfffffff0,0x7fffffff,0x80000000,0x12345678]
    for side in edges:
        for device in edges:
            for source in edges:
                for result in (0,0xfffffffc,0xfffffff5,0x80000000):
                    for swap in (0,1):yield "M",side,device,source,[result]*4,swap
    for i in range(4096):yield "M",rng.getrandbits(32),rng.getrandbits(32),rng.getrandbits(32),[rng.getrandbits(32) for _ in range(4)],i&1


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("repository",type=Path);a=p.parse_args()
    lib=a.repository.resolve()/"uc-library";directory=lib/"recovered-all/client"
    manifest=json.loads((directory/"manifest.json").read_text());binary=a.repository/manifest["path"]
    raw=binary.read_bytes();assert sha(raw)==manifest["sha256"]
    symbols=json.loads((directory/"symbols.json").read_text())
    functions={op:next(s for s in symbols if s["kind"]=="STT_FUNC" and s["demangled"]==name) for op,name in NAMES.items()}
    route=next(s for s in symbols if s["kind"]=="STT_FUNC" and s["demangled"]==ROUTE)
    for s in [*functions.values(),route]:
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
    obj=0x10000000;endpoint1=0x10001000;endpoint2=0x10002000;stack=0x20000000;stop=0x30000000
    u.mem_map(obj,0x3000);u.mem_map(stack,65536);u.mem_map(stop,4096)
    state={};blocks=set()

    def callback(uc,address,size,user):
        endpoint=uc.reg_read(arm.UC_ARM_REG_R0)
        assert endpoint in (endpoint1,endpoint2)
        values=[uc.reg_read(reg) for reg in (arm.UC_ARM_REG_R1,arm.UC_ARM_REG_R2,arm.UC_ARM_REG_R3)]
        values.append(int.from_bytes(uc.mem_read(uc.reg_read(arm.UC_ARM_REG_SP),4),"little"))
        result=state["returns"][len(state["events"])%4]
        state["events"].append([1 if endpoint==endpoint1 else 2,*values])
        if state["swap"]:
            uc.mem_write(obj+0x58,struct.pack("<I",endpoint2 if endpoint==endpoint1 else endpoint1))
        for i,reg in enumerate((arm.UC_ARM_REG_R1,arm.UC_ARM_REG_R2,arm.UC_ARM_REG_R3,arm.UC_ARM_REG_R12)):
            uc.reg_write(reg,0x91000000|(i<<16)|len(state["events"]))
        uc.reg_write(arm.UC_ARM_REG_R0,result)
        uc.reg_write(arm.UC_ARM_REG_PC,uc.reg_read(arm.UC_ARM_REG_LR))

    def block(uc,address,size,user):
        assert address==route["address"] or any(s["address"]<=address<s["address"]+s["size"] for s in functions.values()),hex(address)
        blocks.add(address)

    def memory(uc,access,address,size,value,user):
        allowed=elf_ranges+[(obj,obj+0x5c),(stack,stack+65536)]
        assert any(lo<=address and address+size<=hi for lo,hi in allowed),hex(address)
    u.hook_add(unicorn.UC_HOOK_CODE,callback,begin=route["address"],end=route["address"])
    u.hook_add(unicorn.UC_HOOK_BLOCK,block)
    u.hook_add(unicorn.UC_HOOK_MEM_READ|unicorn.UC_HOOK_MEM_WRITE,memory)
    out=lib/"validation/dice-routing/runs"/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out.mkdir(parents=True,exist_ok=False);path=out/"arm-vectors.txt";counts=Counter();events=0
    with path.open("w") as stream:
        for index,(op,a1,a2,a3,returns,swap) in enumerate(cases()):
            storage=bytearray(b"\xa5"*0x5c);struct.pack_into("<I",storage,0x58,endpoint1)
            u.mem_write(obj,bytes(storage));state.update(events=[],returns=returns,swap=swap)
            u.reg_write(arm.UC_ARM_REG_CPSR,0x10)
            for i in range(13):u.reg_write(getattr(arm,f"UC_ARM_REG_R{i}"),0)
            for reg,value in ((arm.UC_ARM_REG_R0,obj),(arm.UC_ARM_REG_R1,a1),(arm.UC_ARM_REG_R2,a2),(arm.UC_ARM_REG_R3,a3),(arm.UC_ARM_REG_SP,stack+0xff00),(arm.UC_ARM_REG_LR,stop)):
                u.reg_write(reg,value)
            u.emu_start(functions[op]["address"],stop,count=2000)
            assert u.reg_read(arm.UC_ARM_REG_PC)==stop and u.reg_read(arm.UC_ARM_REG_SP)==stack+0xff00
            returned=u.reg_read(arm.UC_ARM_REG_R0);assert returned==0
            if swap and len(state["events"])&1:struct.pack_into("<I",storage,0x58,endpoint2)
            assert bytes(u.mem_read(obj,len(storage)))==storage
            row=[op,*[f"{x:08x}" for x in (a1,a2,a3,*returns,swap,returned,len(state["events"]))]]
            for event in state["events"]:row.extend(f"{x:08x}" for x in event)
            stream.write(" ".join(row)+"\n");counts[op]+=1;events+=len(state["events"])
            if index%20000==0:print(index,dict(counts),flush=True)
    server_symbols=json.loads((lib/"recovered-all/server/symbols.json").read_text())
    assert not any(s.get("demangled") in NAMES.values() for s in server_symbols)
    report=dict(role="client",original_elf_sha256=manifest["sha256"],functions=functions,callback_symbol=route,
        cases=dict(counts),callback_events=events,fixture_sha256=sha(path.read_bytes()),unicorn_version=unicorn.__version__,
        oracle="Original clientmanager ARM instructions plus normal-return setRoute hook; originalsetRoute body, Core, timestamp, UART, wait and hardware not executed",
        callback_contract="Capture opaque endpoint and four32bitroutewords in order; return arbitraryconfiguredword, clobberEABIcaller-saved registers; optionallyreplace manager+0x58 endpointaftereverycall. No actualsubsystemimplementation orownership inferred.",
        state_checks="Original0x5cbyte manager region unchanged exceptexplicitcallbackendpointreplacement; SP restored. Portablecallbacktraces comparedexactly, no hashes.",
        method_blocks={op:[hex(x) for x in sorted(blocks) if s["address"]<=x<s["address"]+s["size"]] for op,s in functions.items()},
        server_methods_absent=True,domain="Profilewords0..65535+5signedboundaries+4096seededrandomwords;validprofiles1/2/3with5returnpatternsandendpointswapping. Monitor9edgewordscubed x4returnwords x2swapchoices+4096randomtriples. Validnon-nullcallbackendpoints; exactorderedtuples/endpointIDs, ignoredcallbackerrors, modulo32sourceDevice+16 andzeroreturn. No transport/ack/timing/device/thread/ARMABI claim.",
        tool_sha256=sha(Path(__file__).read_bytes()))
    (out/"arm-oracle.json").write_text(json.dumps(report,indent=2)+"\n")
    print("COMPLETE",out,dict(counts),"events",events,flush=True)


if __name__=="__main__":main()
