"""Run the sealed ARM application range with explicit Core/allocator boundaries."""

import hashlib
import io
import json
from pathlib import Path
from struct import pack, unpack

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import (
    UC_ARM_REG_LR,
    UC_ARM_REG_PC,
    UC_ARM_REG_R0,
    UC_ARM_REG_R1,
    UC_ARM_REG_R2,
    UC_ARM_REG_R3,
    UC_ARM_REG_SP,
)

TASK = Path(__file__).parent.name
VARIANT = TASK.removeprefix("sqlite02_lcdview_")
PACKET = Path("temp/recovery-work/sqlite-issued/packet") / TASK / "CONTEXT.json"
OBJ, RECT, OBSERVER, VIEW = 0x1000000, 0x1010000, 0x1011000, 0x1012000
STACK, STOP, CAST = 0x1020000, 0x1030000, 0x1031000
ROOT_CONSTRUCT = 0x112988
ROOT_DESTROY = 0x1126D8
ROOT_FOCUS = 0x113514
ROOT_CURRENT_FOCUS = 0x10EF80
DELETE = 0xAD5C


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_inputs():
    original = json.loads(PACKET.read_text())["originals"][0]["original"]
    elf_bytes = Path(original["elf_path"]).read_bytes()
    assert digest(elf_bytes) == original["elf"]
    elf = ELFFile(io.BytesIO(elf_bytes))
    symbols = elf.get_section_by_name(".symtab")
    symbol, = symbols.get_symbol_by_name(original["mangled"])
    section = elf.get_section(symbol["st_shndx"])
    address = symbol["st_value"]
    offset = section["sh_offset"] + address - section["sh_addr"]
    raw = elf_bytes[offset:offset + symbol["st_size"]]
    assert (address, symbol["st_size"], symbol["st_shndx"], offset, section.name) == (
        original["address"], original["size"], original["section"],
        original["file_offset"], original["section_name"]
    )
    assert raw.hex() == original["range_hex"] and digest(raw) == original["range_sha256"]
    named = {
        ROOT_CONSTRUCT: "_ZN4Core8Portable8RootViewC2ERKNS_5TRectIiEENS_17BitmapPixelFormatENS1_10RenderModeE",
        ROOT_DESTROY: "_ZN4Core8Portable8RootViewD2Ev",
        ROOT_FOCUS: "_ZN4Core8Portable8RootView12setFocusViewEPNS0_4ViewE",
        ROOT_CURRENT_FOCUS: "_ZNK4Core8Portable8RootView12getFocusViewEv",
        DELETE: "_ZdlPv@@GLIBCXX_3.4",
        0x7463C: "_ZThn132_N8Presonus16MainLCDComponent21onFocusControlChangedEPN4Core8Portable7ControlE",
        0x734B4: "_ZThn132_N8Presonus16MainLCDComponent11onDestroyedERKNS_7LcdViewE",
        0x74644: "_ZN8Presonus16MainLCDComponent21onFocusControlChangedEPN4Core8Portable7ControlE",
        0x734BC: "_ZN8Presonus16MainLCDComponent11onDestroyedERKNS_7LcdViewE",
    }
    for site, name in named.items():
        assert any(s["st_value"] == site for s in symbols.get_symbol_by_name(name)), (hex(site), name)
    return original, elf, named


def execute(original, elf, named, observed, width, height, fmt, mode, focus_case, repeat):
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    uc.mem_map(0, 0x400000)
    for seg in elf.iter_segments():
        if seg["p_type"] == "PT_LOAD":
            uc.mem_write(seg["p_vaddr"], seg.data())
    for address in (OBJ, RECT, OBSERVER, VIEW, STACK, STOP, CAST):
        uc.mem_map(address, 0x1000)
    observer_iface = OBSERVER + 132
    observer_vtable = 0x19C7C8 + 28 * 4
    view_vtable = VIEW + 0x100
    word = lambda address: unpack("<I", uc.mem_read(address, 4))[0]
    put = lambda address, value: uc.mem_write(address, pack("<I", value))
    assert [word(observer_vtable + i * 4) for i in range(2)] == [0x7463C, 0x734B4]
    put(observer_iface, observer_vtable)
    put(OBSERVER + 0x90, OBJ)
    put(VIEW, view_vtable)
    put(view_vtable, CAST)
    uc.mem_write(RECT, pack("<4i", 0, 0, width, height))
    put(OBJ + 0x204, observer_iface if observed else 0)
    focus_request = VIEW if focus_case else 0
    focus = focus_request if repeat else 0
    state = {"focus": 0, "destroyed": 0, "deallocated": 0}
    calls, writes, observer_writes, pcs = [], [], [], []
    initial_observer = 0x5A5A5A5A
    if VARIANT.endswith("construct"):
        put(OBJ + 0x204, initial_observer)

    def record_write(_uc, _access, address, size, value, _data):
        if OBJ <= address < OBJ + 0x1000:
            writes.append([address - OBJ, size, value])
        if OBSERVER <= address < OBSERVER + 0x1000:
            observer_writes.append([address - OBSERVER, size, value])

    def hook(_uc, address, size, _data):
        nonlocal focus
        r0, r1, r2, r3 = (uc.reg_read(reg) for reg in
                          (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3))
        if address in (0x7463C, 0x734B4):
            assert r0 == observer_iface
            if address == 0x7463C:
                assert r1 == VIEW and focus == VIEW
                state["focus"] += 1
            else:
                assert r1 == OBJ and word(OBJ) == 0x19AE80
                state["destroyed"] += 1
            calls.append([address, named[address], [r0, r1]])
            return
        if address in (0x74644, 0x734BC):
            assert r0 == OBSERVER
            return
        if 0x7463C < address < 0x74654 or 0x734B4 < address < 0x734DC:
            return
        if address == CAST:
            assert r0 == VIEW and r1 == 0x436E746C
            calls.append([address, "Control cast boundary", [r0, r1]])
            uc.reg_write(UC_ARM_REG_R0, VIEW if focus_case == 2 else 0)
        elif address in (ROOT_CONSTRUCT, ROOT_DESTROY, ROOT_FOCUS, ROOT_CURRENT_FOCUS, DELETE):
            assert r0 == OBJ
            calls.append([address, named[address], [r0, r1, r2, r3]])
            if address == ROOT_CONSTRUCT:
                assert (r1, r2, r3) == (RECT, fmt, mode)
                assert unpack("<4i", uc.mem_read(r1, 16)) == (0, 0, width, height)
            elif address == ROOT_FOCUS:
                assert r1 == focus_request
                focus = r1
            elif address == ROOT_CURRENT_FOCUS:
                uc.reg_write(UC_ARM_REG_R0, focus)
            elif address == DELETE:
                uc.mem_unmap(OBJ, 0x1000)
                state["deallocated"] += 1
        else:
            assert original["address"] <= address < address + size <= original["address"] + original["size"], hex(address)
            pcs.append(address)
            return
        uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

    uc.hook_add(UC_HOOK_CODE, hook)
    uc.hook_add(UC_HOOK_MEM_WRITE, record_write)
    uc.reg_write(UC_ARM_REG_SP, STACK + 0x800)
    uc.reg_write(UC_ARM_REG_LR, STOP)
    uc.reg_write(UC_ARM_REG_R0, OBJ)
    uc.reg_write(UC_ARM_REG_R1, RECT if VARIANT.endswith("construct") else focus_request)
    uc.reg_write(UC_ARM_REG_R2, fmt)
    uc.reg_write(UC_ARM_REG_R3, mode)
    uc.emu_start(original["address"], STOP, count=128)
    assert uc.reg_read(UC_ARM_REG_PC) == STOP
    if VARIANT.endswith("construct"):
        assert word(OBJ + 0x204) == 0
        assert [call[0] for call in calls] == [ROOT_CONSTRUCT]
    elif VARIANT.endswith("destroy"):
        expected = ([0x734B4] if observed else []) + [ROOT_DESTROY]
        if VARIANT == "deleting_destroy":
            expected.append(DELETE)
        assert [call[0] for call in calls] == expected
        assert word(OBSERVER + 0x90) == (0 if observed else OBJ)
        assert observer_writes == ([[0x90, 4, 0]] if observed else [])
    else:
        expected = [ROOT_FOCUS] + ([ROOT_CURRENT_FOCUS] if observed else [])
        if observed and focus_request:
            expected += [CAST] + ([0x7463C] if focus_case == 2 else [])
        assert [call[0] for call in calls] == expected
    return {
        "arguments": [observed, width, height, fmt, mode, focus_case, repeat],
        "observation": list(state.values()),
        "native_pcs": pcs,
        "native_receiver_writes": writes,
        "native_observer_writes": observer_writes,
        "native_boundary_calls": calls,
    }


def generate():
    original, elf, named = read_inputs()
    if VARIANT.endswith("construct"):
        args = [(0, 28, 16, 0, 0, 0, 0), (0, 32, 24, 1, 1, 0, 0), (0, 8, 8, 2, 2, 0, 0)]
    elif VARIANT.endswith("destroy"):
        args = [(obs, 16, 12, 0, mode, 0, 0) for obs in (0, 1) for mode in (0, 1, 2)]
    else:
        args = [(obs, 16, 12, 0, 0, focus, repeat) for obs in (0, 1)
                for focus in (0, 1, 2) for repeat in (0, 1)]
    return {"original": original, "variant": VARIANT,
            "boundary": "Native application opcodes and native MainLCD observer thunks. Core calls mediated at verified entry points with real pinned CCL exercised in portable replay. Native delete PLT releases the exact emulated arena page in the allocator boundary, with real portable operator delete separately observed.",
            "cases": [execute(original, elf, named, *case) for case in args]}


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2, sort_keys=True))
