"""Execute scoped original ARM instructions with offline provider boundaries."""

import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP,
)

ROOT = Path(__file__).resolve().parents[4]
ELF = ROOT / "rootfs/RML16AI_Rack_13731/home/root/mixer"
PACKETS = ROOT / "temp/recovery-work/sqlite-issued/packet"
APP, CARD, ENDPOINT, SPI = 0x1000000, 0x1001000, 0x1002000, 0x1003000
STACK, STOP = 0x1100000, 0x1200000
CARD_PREFIX = "_ZN8Presonus4NOAA17TCardUCNetHandler"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inspect(elf, variant):
    packet = PACKETS / f"sqlite05_mixer_application_{variant}" / "CONTEXT.json"
    original, = json.loads(packet.read_text())["originals"]
    original = original["original"]
    elf.stream.seek(0)
    raw = elf.stream.read()
    assert digest(raw) == original["elf"]
    table = elf.get_section_by_name(".symtab")

    def resolve(name):
        symbol, = table.get_symbol_by_name(name)
        section_index = symbol["st_shndx"]
        section = elf.get_section(section_index)
        address, size = symbol["st_value"], symbol["st_size"]
        data = None
        if section["sh_type"] != "SHT_NOBITS":
            offset = address - section["sh_addr"] + section["sh_offset"]
            data = raw[offset:offset + size]
            assert len(data) == size
        else:
            offset = None
        return {
            "mangled": name, "size": size, "address": address,
            "file_offset": offset, "section": section_index,
            "section_name": section.name,
            "range_sha256": digest(data) if data is not None else None,
        }, data

    target, target_bytes = resolve(original["mangled"])
    assert all(target[key] == original[key] for key in target)
    assert target_bytes.hex() == original["range_hex"]
    provider = {}
    for name in [
        CARD_PREFIX + "D0Ev", "_ZN8Presonus2UC12DiceEndPointD0Ev",
        "_ZTVN8Presonus4NOAA17TCardUCNetHandlerE",
        "_ZTVN8Presonus2UC12DiceEndPointE",
        "_ZTVN8Presonus5Mixer16MixerApplicationE",
        "_ZTIN8Presonus5Mixer16MixerApplicationE",
        "_ZTVN8Presonus3Dsp17OMAPTargetHandlerE", "_ZL8mixerapp",
        "_ZL13signalHandleri",
    ]:
        provider[name] = resolve(name)[0]
    plt = elf.get_section_by_name(".plt")
    relocations = elf.get_section_by_name(".rel.plt")
    dynamic = elf.get_section(relocations["sh_link"])
    bindings = {}
    for entry, expected in [(0xA7CC, "signal"), (0xAC10, "_ZdlPv")]:
        index, remainder = divmod(entry - plt["sh_addr"] - 20, 12)
        assert remainder == 0
        relocation = relocations.get_relocation(index)
        name = dynamic.get_symbol(relocation["r_info_sym"]).name
        assert name == expected, name
        bindings[name] = {
            "entry": entry, "relocation_index": index, "got": relocation["r_offset"],
        }
    return original, target, provider, bindings


def execute(elf, target, providers, variant, live, executable):
    emulator = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    emulator.mem_map(0, 0x800000)
    for segment in elf.iter_segments():
        if segment["p_type"] == "PT_LOAD":
            emulator.mem_write(segment["p_vaddr"], segment.data())
    for address, size in [(APP, 0x4000), (STACK, 0x10000), (STOP, 0x1000)]:
        emulator.mem_map(address, size)

    def put_word(address, value):
        emulator.mem_write(address, struct.pack("<I", value))

    def word(address):
        return struct.unpack("<I", emulator.mem_read(address, 4))[0]

    def byte(address):
        return emulator.mem_read(address, 1)[0]

    card_d0 = providers[CARD_PREFIX + "D0Ev"]
    endpoint_d0 = providers["_ZN8Presonus2UC12DiceEndPointD0Ev"]
    card_vptr = providers["_ZTVN8Presonus4NOAA17TCardUCNetHandlerE"]["address"] + 8
    endpoint_vptr = providers["_ZTVN8Presonus2UC12DiceEndPointE"]["address"] + 8
    app_vptr = providers["_ZTVN8Presonus5Mixer16MixerApplicationE"]["address"] + 8
    omap_vptr = providers["_ZTVN8Presonus3Dsp17OMAPTargetHandlerE"]["address"] + 8
    current = providers["_ZL8mixerapp"]["address"]
    assert word(card_vptr + 12) == card_d0["address"]
    assert word(endpoint_vptr + 32) == endpoint_d0["address"]

    emulator.mem_write(APP, b"\xA5" * 0x40)
    put_word(APP + 8, CARD if live else 0)
    put_word(CARD, card_vptr)
    put_word(CARD + 0x5C, ENDPOINT)
    put_word(ENDPOINT, endpoint_vptr)
    put_word(0x495368, SPI)
    allocations = {APP: "APP_FREE"}
    if live:
        allocations.update({CARD: "S", ENDPOINT: "E"})

    def defaults():
        return [
            byte(APP + 0xC), byte(APP + 0xD),
            *(word(APP + offset) for offset in (0x10, 0x14, 0x1C, 0x20)),
            *(word(APP + offset) for offset in range(0x28, 0x40, 4)),
        ]

    trace = []
    writes = []
    calls = []
    pcs = []
    registered_defaults = None
    service = None
    if live:
        service = subprocess.Popen(
            [str(executable.resolve()), "provider", "D0", "1", "1", "1", "1", "0"],
            cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
        )

    def provider(operation):
        assert service is not None
        service.stdin.write(operation + "\n")
        service.stdin.flush()
        observed = service.stdout.readline().split()
        assert observed
        trace.extend(observed)
        return observed

    def write_hook(_, _access, address, size, value, _data):
        if not STACK <= address < STACK + 0x10000:
            assert APP <= address < APP + 0x4000 or address == current, hex(address)
            writes.append([address, size, value])

    def return_to_caller():
        emulator.reg_write(UC_ARM_REG_PC, emulator.reg_read(UC_ARM_REG_LR))

    def code_hook(_, address, size, _data):
        nonlocal registered_defaults
        a0 = emulator.reg_read(UC_ARM_REG_R0)
        a1 = emulator.reg_read(UC_ARM_REG_R1)
        if address == 0xA7CC:
            assert variant in ("c1", "c2")
            assert a0 == 2 and a1 == providers["_ZL13signalHandleri"]["address"]
            assert word(current) == APP and word(APP + 0x24) == omap_vptr
            registered_defaults = defaults()
            calls.append(["signal", a0, a1, word(current)])
            emulator.reg_write(UC_ARM_REG_R0, 1)  # Modeled SIG_IGN predecessor.
        elif address == 0xA2FE0:
            assert (a0, a1) == (SPI, CARD)
            assert provider("U") == ["U"]
            calls.append(["offline_current_source_spi_unregister", a1])
        elif address == 0x1046C8:
            assert a0 in (CARD + 0x34, CARD + 0xC)
            operation, queue = ("O", "QO") if a0 == CARD + 0x34 else ("I", "QI")
            assert provider(operation) == [queue, "P"]
            calls.append(["offline_current_source_queue_destroy", a0])
        elif address == 0xAC10:
            kind = allocations.pop(a0)
            if kind == "E":
                assert provider("E") == ["E"]
            else:
                trace.append(kind)
            calls.append(["executed_native_operator_delete_entry", a0])
            emulator.mem_unmap(a0, 0x1000)
        else:
            allowed = [target] if not live else [target, card_d0, endpoint_d0]
            assert any(
                item["address"] <= address and address + size <= item["address"] + item["size"]
                for item in allowed
            ), hex(address)
            pcs.append(address)
            return
        return_to_caller()

    emulator.hook_add(UC_HOOK_CODE, code_hook)
    emulator.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    emulator.reg_write(UC_ARM_REG_R0, APP)
    emulator.reg_write(UC_ARM_REG_SP, STACK + 0xFF00)
    emulator.reg_write(UC_ARM_REG_LR, STOP)
    try:
        emulator.emu_start(target["address"], STOP, count=1000)
        assert emulator.reg_read(UC_ARM_REG_PC) == STOP
    finally:
        if service is not None:
            service.stdin.close()
            assert service.wait(timeout=10) == 0

    result = {
        "live_card": live, "calls": calls, "writes": writes,
        "instructions": len(pcs),
        "pc_sequence_sha256": digest(b"".join(struct.pack("<I", pc) for pc in pcs)),
        "return_word": emulator.reg_read(UC_ARM_REG_R0),
    }
    if variant in ("c1", "c2"):
        assert registered_defaults is not None
        assert word(APP) == app_vptr and word(APP + 4) == app_vptr + 0x34
        assert word(APP + 8) == 0
        assert word(APP + 0x24) == omap_vptr and word(current) == APP
        assert byte(APP + 0xE) == 0xA5 and byte(APP + 0xF) == 0xA5
        assert word(APP + 0x18) == 0xA5A5A5A5
        assert word(word(APP + 4) - 8) == 0xFFFFFFFC
        app_rtti = providers["_ZTIN8Presonus5Mixer16MixerApplicationE"]["address"]
        assert word(word(APP + 4) - 4) == word(word(APP) - 4) == app_rtti
        result["portable"] = [
            ["REGISTER", *map(str, registered_defaults)],
            ["DEFAULTS", *map(str, defaults())],
            ["INTERFACES", "1", "1"],
        ]
    elif variant == "network_ready":
        assert not writes and not calls
        result["portable"] = [[str(result["return_word"])] * 2]
    else:
        assert writes[:2] == [[APP, 4, app_vptr], [APP + 4, 4, app_vptr + 0x34]]
        assert (APP not in allocations) == (variant == "d0")
        if live:
            assert card_d0["address"] in pcs and endpoint_d0["address"] in pcs
            assert CARD not in allocations and ENDPOINT not in allocations
        result["portable"] = [(["DERIVED"] if variant == "d2" else []) + trace]
    return result


def generate(variant, executable):
    with ELF.open("rb") as stream:
        elf = ELFFile(stream)
        original, target, support, bindings = inspect(elf, variant)
        cases = [
            execute(elf, target, support, variant, live, executable)
            for live in ([False, True] if variant in ("d0", "d1", "d2") else [False])
        ]
    return {
        "version": 1, "elf_sha256": original["elf"], "target": target,
        "support": support, "plt_bindings": bindings, "cases": cases,
    }


if __name__ == "__main__":
    print(json.dumps(generate(sys.argv[1], Path(sys.argv[2])), indent=2))
