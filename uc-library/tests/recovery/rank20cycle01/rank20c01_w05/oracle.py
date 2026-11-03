"""Execute original app instructions only; capture, never emulate, Core boundary.
The boundary hook returns unchanged memory. This isolates app vtable stores and
call arguments, and is explicitly NOT native Core lifecycle verification.
"""
import hashlib, json, sys
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC
ROOT = Path(__file__).resolve().parents[5]
PACKETS = ROOT / "temp/recovery-work/ranked20-cycle01/batch02/packets"
def observe(index, fill):
    packet = PACKETS / f"rank20c01_w05_{index:02}"
    n = json.loads((packet / "native-context.json").read_text())
    body = n["bodies"][n["roots"][0]]
    binary = next(iter(n["binaries"].values()))
    elf = ROOT / binary["path"]
    data = elf.read_bytes()
    assert hashlib.sha256(data).hexdigest() == binary["id"]
    assert hashlib.sha256(data[body["file_offset"]:body["file_offset"] + body["size"]]).hexdigest() == body["bytes_sha256"]
    u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    u.mem_map(0, 0x1000000)
    with elf.open("rb") as f:
        for segment in ELFFile(f).iter_segments():
            if segment["p_type"] == "PT_LOAD": u.mem_write(segment["p_vaddr"], segment.data())
    obj, name, stack, stop = 0x800000, 0x810000, 0x900000, 0xA00000
    u.mem_write(obj, bytes([fill]) * 1024)
    u.mem_write(name, b"filter_group\0")
    for register, value in [(UC_ARM_REG_R0,obj),(UC_ARM_REG_R1,name),(UC_ARM_REG_SP,stack),(UC_ARM_REG_LR,stop)]: u.reg_write(register,value)
    calls, writes = [], []
    target = 0x11a53c if index == 19 else 0xf6160
    def code(uc, address, size, _):
        if address == stop: uc.emu_stop()
        elif address == target:
            calls.append({"address":address,"r0":uc.reg_read(UC_ARM_REG_R0),"r1":uc.reg_read(UC_ARM_REG_R1),"writes_before_boundary":len(writes)})
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
        elif not body["address"] <= address < body["address"] + body["size"]:
            raise RuntimeError(f"unexpected instruction {address:x}")
    def write(uc, access, address, size, value, _):
        if obj <= address < obj+1024: writes.append({"offset":address-obj,"size":size,"value":value})
    u.hook_add(UC_HOOK_CODE, code); u.hook_add(UC_HOOK_MEM_WRITE, write)
    u.emu_start(body["address"],stop,count=1000)
    assert len(calls)==1 and calls[0]["r0"]==obj
    assert [w["offset"] for w in writes]==[0,4]
    assert calls[0]["writes_before_boundary"]==(2 if index==19 else 0)
    return {"task_id":packet.name,"fill":fill,"range":{k:body[k] for k in ["address","size","section","file_offset","bytes_sha256"]},"boundary_calls":calls,"app_memory_writes":writes,"returned_this":u.reg_read(UC_ARM_REG_R0)==obj}
def main():
    result={"scope":"Original app instructions with test-only Core call capture, no Core native body executed", "cases":[observe(i,f) for i in [19,20] for f in [0,165,255]]}
    fixture=Path(__file__).with_name("fixtures.json")
    if "--capture" in sys.argv: fixture.write_text(json.dumps(result,indent=2)+"\n")
    else: assert json.loads(fixture.read_text())==result
    print("6 native caller cases passed; Core behavior excluded")
if __name__=="__main__": main()
