"""Replay exact application meter extents and explicit provider boundaries."""
import ctypes
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UcError, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0 as R0, UC_ARM_REG_R1 as R1, UC_ARM_REG_R2 as R2, UC_ARM_REG_PC as PC, UC_ARM_REG_LR as LR, UC_ARM_REG_SP as SP

TASK = Path(__file__).parent.name
MODE = int(TASK[-2:])
ROOT = "_ZN8Presonus15MeterBallistics"
MAID = "_ZN8Presonus9MeterMaid"
TABLE = ROOT + "15MeterDecayTableC1EPKf"
OBJ, IN, STACK, STOP = (0x22000000, 0x23000000, 0x24000000, 0x25000000)
TABLE_INPUT = (-72., -45., -20., -6., -2., 0.)
POW = ctypes.CDLL("libm.so.6").powf
POW.argtypes = [ctypes.c_float, ctypes.c_float]
POW.restype = ctypes.c_float
PLAN, CONTEXT, REVIEW, TABLE_REVIEW, *ELFS = map(Path, sys.argv[1:])
target_rows = json.loads(PLAN.read_text())["targets"]
bounds = re.findall(r'ELF `([0-9a-f]{64})`.*?original `([^`]+)`.*?SHA256 `([0-9a-f]{64})`',
                    CONTEXT.read_text())
RANGE_HASHES = {(elf, name): digest for elf, name, digest in bounds}
prior = json.loads(REVIEW.read_text())
table_prior = json.loads(TABLE_REVIEW.read_text())


def dig(data):
    return hashlib.sha256(data).hexdigest()


def pack(*values):
    return struct.pack(f"<{len(values)}I", *values)


def bits(value):
    return struct.unpack("<I", struct.pack("<f", value))[0]


def fl(value):
    return struct.unpack("<f", pack(value))[0]


def observe(target, path):
    with path.open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == target["original_elf_sha256"]
        stream.seek(0)
        elf = ELFFile(stream)
        symtab = elf.get_section_by_name(".symtab")
        sections = list(elf.iter_sections())
        segments = [(s["p_vaddr"], s["p_memsz"], s.data())
                    for s in elf.iter_segments() if s["p_type"] == "PT_LOAD"]
        imports = elf.get_section_by_name(".rel.plt")
        dynsym = elf.get_section(imports["sh_link"])
        plt = elf.get_section_by_name(".plt")
        plt_table = {dynsym.get_symbol(rel["r_info_sym"]).name: plt["sh_addr"] + 20 + 12 * i
                     for i, rel in enumerate(imports.iter_relocations()) if rel["r_info_type"] == 22}

        def span(name):
            sym, = symtab.get_symbol_by_name(name)
            section_index = sym["st_shndx"]
            section = sections[section_index]
            address, size = sym["st_value"], sym["st_size"]
            rel = address - section["sh_addr"]
            assert 0 <= rel <= section["sh_size"] - size
            data = section.data()[rel:rel+size]
            return dict(mangled=name, address=address, size=size, section=section.name,
                        section_index=section_index, file_offset=section["sh_offset"] + rel,
                        sha256=dig(data)), data

        extent, code = span(target["mangled"])
        identity = target["original_elf_sha256"], target["mangled"]
        assert extent["sha256"] == RANGE_HASHES[identity]
        assert (extent["address"], extent["size"], extent["section_index"]) == (
            target["address"], target["size"], target["section"])
        related = {}
        for name in ("__aeabi_fsub", "__aeabi_fmul", "__aeabi_fdiv", "__aeabi_fcmplt",
                     "__aeabi_cfcmple", "__cmpsf2"):
            if MODE in (8, 11, 12, 13):
                related[name] = span(name)[0]
        if MODE in (8, 13):
            related[TABLE] = span(TABLE)[0]
            assert related[TABLE]["sha256"] == {
                "server": "6650cc8a51515a686b91fade908e6cbc8476d914037a5145d2abd4b94a228e28",
                "client": "82fa7d7dfaa420fe638e85975a0a2a3cc5c7d812d507eb9c19bef2972cddcb43",
            }[target["role"]]
            if MODE == 13:
                related[ROOT+"C2Ev"] = span(ROOT+"C2Ev")[0]
                _, base = span(ROOT+"C2Ev")
            else:
                base = code
            base_vptr, decay_rate, guard, table, defaults = struct.unpack("<5I", base[-20:])
        if MODE in (19,20):
            d1 = target["mangled"].replace("D0E","D1E")
            related[d1] = span(d1)[0]
            assert not symtab.get_symbol_by_name(target["mangled"].replace("D0E","D2E"))
            base_vptr, = struct.unpack("<I", code[-4:])
        if MODE in (14,15):
            provider = "_ZN4Core8Portable12NumericParam8setValueEfb"
            params, _ = span("_ZTVN4Core8Portable12NumericParamE")
            related[provider] = span(provider)[0]
            assert params["address"] == next(x["true_typed_numeric_provider"]["vtable_elf_address"]
                for x in prior["exact_originals"].values() if x["elf_sha256"] == identity[0])
    if MODE in (19,20):
        owner = "MeterBallistics" if MODE == 19 else "MeterMaid"
        review = prior["verified_class_collateral"][owner][identity[0]]
        seeds = [case["seed"] for case in review["variants"]["D0"]["native_cases"]]
        assert review["variants"]["D1"]["range_sha256"] == related[d1]["sha256"]
        assert review["variants"]["D0"]["actual_deallocator"] == plt_table["_ZdlPv"]
        points = [(seed, variant) for seed in seeds for variant in ("D0","D1")]
    else:
        [old] = [r for r in prior["exact_originals"].values()
                 if (r["elf_sha256"],r["original_mangled"]) == identity]
        assert old["range_sha256"] == extent["sha256"]
        if MODE in (14,15):
            points = [(r["bound"],r["input_bits"]) for r in old["cases"]]
        elif MODE == 13:
            points = [(0,), (1,)]
        else:
            points = [tuple(r["inputs"]) for r in old["cases"]]

    def make_cpu():
        uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        low = min(a for a,_,_ in segments) & ~4095
        high = max(a+n for a,n,_ in segments)
        uc.mem_map(low,(high-low+4095)&~4095)
        for addr,_,data in segments:
            uc.mem_write(addr,data)
        for addr in (OBJ,IN,STACK,STOP):
            uc.mem_map(addr,4096)
        assert dig(bytes(uc.mem_read(extent["address"],extent["size"]))) == extent["sha256"]
        for row in related.values():
            assert dig(bytes(uc.mem_read(row["address"],row["size"]))) == row["sha256"]
        return uc

    persistent = make_cpu() if MODE in (8,13) else None
    cases = []
    for point in points:
        uc = persistent or make_cpu()
        uc.mem_write(OBJ,b"\xa5"*96)
        traces, writes, events = [], [], []
        entry = extent
        expected_vptr = None

        def word(a):
            return struct.unpack("<I",uc.mem_read(a,4))[0]

        def words(a,n):
            return list(struct.unpack(f"<{n}I",uc.mem_read(a,n*4)))

        def write(a,*value):
            uc.mem_write(a,pack(*value))

        if MODE in (8,13):
            assert bool(word(guard) & 1) == bool(point[0])
            assert tuple(map(fl,words(defaults,6))) == TABLE_INPUT
            expected_vptr = base_vptr if MODE == 8 else struct.unpack("<I",code[-4:])[0]
        elif MODE == 9:
            write(OBJ+0x18,point[0])
        elif MODE == 10:
            write(OBJ+0x18,point[0])
        elif MODE in (11,12):
            has_table,value,rate=point
            write(OBJ+0x2c,IN if has_table else 0)
            write(OBJ+(0x14 if MODE==11 else 0x18),bits(value))
            write(OBJ+0xc,bits(rate))
            # Reviewed synthetic provider table data, used only for input to the getter.
            write(IN,*next(row["cases"][0]["outputs"] for row in table_prior["exact_originals"].values()
                           if row["elf_sha256"] == identity[0]))
        elif MODE in (14,15):
            bound,value=point
            slot=0x30 if MODE==14 else 0x34
            write(OBJ+slot,IN if bound else 0)
            if bound:
                vptr=params["address"]+8
                addr=related[provider]["address"]
                assert word(vptr+88)==addr==old["true_typed_numeric_provider"]["setValue_elf_address"]
                assert dig(bytes(uc.mem_read(params["address"],params["size"]))) == old["true_typed_numeric_provider"]["range_sha256"]
                write(IN,vptr)
        else:
            seed,variant=point
            expected_vptr=base_vptr
            uc.mem_write(OBJ,bytes([seed])*96)
            entry=extent if variant=="D0" else related[d1]
        before=bytes(uc.mem_read(OBJ,96))
        boundary_names = {plt_table[x]: x for x in ("powf","__cxa_guard_acquire","__cxa_guard_release","_ZdlPv") if x in plt_table}
        spans = [entry,*related.values()]

        def on_exec(machine,pc,_size,_data):
            traces.append(pc)
            x,y=machine.reg_read(R0),machine.reg_read(R1)
            name=boundary_names.get(pc)
            if name=="powf" and MODE in (8,13):
                machine.reg_write(R0,bits(POW(fl(x),fl(y))))
            elif name=="__cxa_guard_acquire" and MODE in (8,13):
                assert x==guard
                events.append("guard_acquire")
                machine.reg_write(R0,int(not word(x)&1))
            elif name=="__cxa_guard_release" and MODE in (8,13):
                assert x==guard
                events.append("guard_release")
                write(guard,1)
            elif name=="_ZdlPv" and MODE in (19,20):
                assert point[1]=="D0" and x==OBJ and word(x)==expected_vptr
                assert bytes(machine.mem_read(OBJ+4,92))==before[4:]
                machine.mem_unmap(x,4096)
                events.append("same_receiver_unmapped")
            elif MODE in (14,15) and pc==related[provider]["address"]:
                assert x==IN and machine.reg_read(R2)==0
                events.append(["actual_NumericParam_setValue_slot",y,False])
            else:
                assert any(r["address"]<=pc<r["address"]+r["size"] for r in spans),hex(pc)
                return
            machine.reg_write(PC,machine.reg_read(LR))

        def on_write(_uc,_access,address,size,value,_data):
            if OBJ<=address<OBJ+96:
                writes.append([address-OBJ,size,value&0xffffffff])

        hc=uc.hook_add(UC_HOOK_CODE,on_exec)
        hw=uc.hook_add(UC_HOOK_MEM_WRITE,on_write)
        for reg,value in ((R0,OBJ),(R1,point[1] if MODE in (14,15) else 0),
                          (SP,STACK+2048),(LR,STOP)):
            uc.reg_write(reg,value)
        uc.emu_start(entry["address"],STOP,count=12000)
        assert (uc.reg_read(PC),uc.reg_read(SP))==(STOP,STACK+2048)
        uc.hook_del(hc)
        uc.hook_del(hw)
        result = None
        if MODE in (8,13):
            assert word(OBJ)==expected_vptr and word(OBJ+0x2c)==table
            assert words(OBJ+0x14,6)==[0]*6
            result=[uc.mem_read(OBJ+4,1)[0],word(OBJ+8),word(OBJ+0xc),
                    uc.mem_read(OBJ+0x10,1)[0],*words(OBJ+0x14,6),*words(table,10)]
            assert events==(["guard_acquire","guard_release"] if not point[0] else [])
            if MODE==13:
                assert words(OBJ+0x30,4)==[0]*4
                result.extend(words(OBJ+0x30,4))
                assert related[ROOT+"C2Ev"]["address"] in traces
            elif not point[0]:
                assert result[10:20]==old["cases"][0]["outputs"]
        elif MODE in (9,11,12):
            assert bytes(uc.mem_read(OBJ,96))==before
            result=[uc.reg_read(R0)]
            assert result==old["cases"][len(cases)]["outputs"]
        elif MODE==10:
            assert bytes(uc.mem_read(OBJ,20))==before[:20] and bytes(uc.mem_read(OBJ+44,52))==before[44:]
            result=words(OBJ+20,6)
            assert result==old["cases"][len(cases)]["outputs"]
        elif MODE in (14,15):
            assert bytes(uc.mem_read(OBJ,96))==before
            assert events==old["cases"][len(cases)]["events"]
            result=[int(bool(events))]
        else:
            try:
                uc.mem_read(OBJ,4)
                mapped=True
            except UcError:
                mapped=False
            assert mapped==(point[1]=="D1")
            if mapped:
                assert word(OBJ)==expected_vptr and bytes(uc.mem_read(OBJ+4,92))==before[4:]
            else:
                assert events==["same_receiver_unmapped"]
            result=[int(not mapped)]
        cases.append(dict(input=list(point),output=result,writes=writes,events=events,
                          trace_count=len(traces)))
    return dict(target=target,elf_path=str(path),extent=extent,related=related,
                plt={k:plt_table[k] for k in ("powf","__cxa_guard_acquire","__cxa_guard_release","_ZdlPv") if k in plt_table},cases=cases)


role_files=dict(zip(("server","client"),ELFS,strict=True))
print(json.dumps({"originals":[observe(t,role_files[t["role"]]) for t in target_rows]},indent=2))
