"""Execute sealed ARM ranges, with pinned CCL operations over a typed bridge."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP,
)

ROOT = Path(__file__).resolve().parents[4]
TASK_PREFIX = "sqlite03_fat_channel_clipboard_"
PACKETS = ROOT / "temp/recovery-work/sqlite-issued/packet"
TAG = 15001
TAG_LOOKUP = "_ZNK4Core8Portable9Component17getParameterByTagEi"
RESIZE = "_ZN4Core6VectorIPNS_8Portable9ComponentEE6resizeEi"
COMPARE = ("__aeabi_fcmpgt", "__aeabi_cfrcmple", "__gesf2")
RESET = "_ZN4Core8Portable12NumericParam10resetValueEb"
VALUE = "_ZNK4Core8Portable12NumericParam8getValueEv"

OBJECT = 0x1000000
ROSTER = OBJECT + 0x100
OUTPUT = OBJECT + 0x200
ITEMS = OBJECT + 0x300
VTABLE = OBJECT + 0x500
COMPONENTS = 0x1010000
GROUPS = 0x1020000
PARAMETERS = 0x1030000
STACK = 0x1040000
STOP = OBJECT + 0x800


def digest(data):
    return hashlib.sha256(data).hexdigest()


def word(value):
    return struct.pack("<I", value)


def bits(value):
    return struct.unpack("<I", struct.pack("<f", value))[0]


def component(id_):
    return COMPONENTS + id_ * 0x100 if id_ else 0


def component_id(pointer):
    return (pointer - COMPONENTS) // 0x100 if pointer else 0


def fixture_input(case):
    def array(values):
        return [len(values), *values]

    return " ".join(map(str, [
        len(case["params"]), *(field for param in case["params"] for field in param),
        case["prior"], case["source"], len(case["groups"]),
        *(field for group in case["groups"] for field in array(group)),
        case["capacity"], *array(case["existing"]),
    ])) + "\n"


def inputs(mode):
    params = [
        [TAG, bits(.25), bits(5.)],
        [TAG, bits(.75), bits(.75)],
        [TAG, bits(-.5), bits(-3.)],
        [TAG, bits(2.), bits(0.)],
        [TAG, bits(1.5), 0x7FC01234],
        [TAG + 1, bits(.5), bits(9.)],
        [0, 0, 0],
        [TAG, bits(-2.), bits(-0.)],
    ]
    mixed = [[7, 1, 0, 6, 3, 2], [], [4, 5, 8, 1, 2, 1, 2]]
    cases = [
        (0, 1, [], 0, []),
        (1, 0, [], 5, [1, 1]),
        (1, 7, [[], [0, 6, 7]], 5, [7]),
        (1, 0, mixed, 5, [1, 2, 1, 0, 6]),
        (0, 1, mixed[::-1], 0, []),
        (1, 3, [mixed[0], mixed[0]], 20, [3, 3, 0]),
    ]
    return [
        dict(params=params, prior=prior, source=source, groups=groups,
             capacity=capacity, existing=existing)
        for prior, source, groups, capacity, existing in cases
    ]


def read_image(mode):
    packet = PACKETS / (TASK_PREFIX + mode) / "CONTEXT.json"
    bound = json.loads(packet.read_text())["originals"][0]["original"]
    image = (ROOT / bound["elf_path"]).read_bytes()
    assert digest(image) == bound["elf"]
    with (ROOT / bound["elf_path"]).open("rb") as stream:
        elf = ELFFile(stream)
        symbols = elf.get_section_by_name(".symtab")

        def record(name):
            original, = symbols.get_symbol_by_name(name)
            address = original["st_value"]
            size = original["st_size"]
            section = original["st_shndx"]
            mapped = elf.get_section(section)
            assert mapped.name == ".text"
            offset = mapped["sh_offset"] + address - mapped["sh_addr"]
            assert mapped["sh_addr"] <= address < address + size <= mapped["sh_addr"] + mapped["sh_size"]
            raw = image[offset:offset + size]
            return dict(mangled=name, address=address, size=size, section=section,
                        file_offset=offset, range_sha256=digest(raw)), raw

        original, raw = record(bound["mangled"])
        assert raw.hex() == bound["range_hex"]
        assert all(value == bound[key] for key, value in original.items())
        assert struct.unpack("<I", raw[-4:])[0] == TAG
        helpers = [record(name) for name in COMPARE] if mode != "copy" else []
        providers = {name: record(name)[0] for name in (TAG_LOOKUP, RESIZE, RESET, VALUE)}
        vtable, = symbols.get_symbol_by_name("_ZTVN4Core8Portable12NumericParamE")
        section = elf.get_section(vtable["st_shndx"])
        table = section["sh_offset"] + vtable["st_value"] - section["sh_addr"] + 8
        for slot, name in [(0x44, VALUE), (0x5C, RESET)]:
            assert struct.unpack_from("<I", image, table + slot)[0] == providers[name]["address"]
        return bound, [(original, raw), *helpers], providers


def observe(executable, mode, case, bodies, providers):
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    pages = set()

    def map_range(address, size):
        for page in range(address & ~4095, (address + size + 4095) & ~4095, 4096):
            if page not in pages:
                uc.mem_map(page, 4096)
                pages.add(page)

    def put(address, *values):
        uc.mem_write(address, b"".join(word(value) for value in values))

    def get(address):
        return struct.unpack("<I", uc.mem_read(address, 4))[0]

    for record, raw in bodies:
        map_range(record["address"], len(raw))
        uc.mem_write(record["address"], raw)
    for record in providers.values():
        map_range(record["address"], 4)
    map_range(OBJECT, 0x51000)
    for index, group in enumerate(case["groups"]):
        address = GROUPS + 0x200 * index
        put(ROSTER + index * 4, address)
        put(address + 0x58, address + 0x100, len(group))
        put(address + 0x100, *(component(child) for child in group))
    for id_ in range(1, len(case["params"]) + 1):
        put(PARAMETERS + 0x100 * id_, VTABLE)
    put(VTABLE + 0x44, providers[VALUE]["address"])
    put(VTABLE + 0x5C, providers[RESET]["address"])
    put(OBJECT + 4, component(case["prior"]))
    put(OBJECT + 0xC, ROSTER, len(case["groups"]))
    put(ITEMS, *(component(id_) for id_ in case["existing"]))
    trace, calls, writes = [], [], []
    executed = Counter()

    with subprocess.Popen([str(executable), "provider"], text=True, bufsize=1,
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE) as process:
        process.stdin.write(fixture_input(case))

        def rpc(command):
            process.stdin.write(command + "\n")
            process.stdin.flush()
            line = process.stdout.readline()
            assert line, (command, process.poll())
            return line.split()

        put(OUTPUT + 4, ITEMS, len(case["existing"]), int(rpc("capacity")[0]))

        def hook(arm, address, size, unused):
            for record, _ in bodies:
                if record["address"] <= address < record["address"] + record["size"]:
                    executed[record["mangled"]] += 1
                    return
            arg0, arg1 = (arm.reg_read(reg) for reg in (UC_ARM_REG_R0, UC_ARM_REG_R1))
            symbol, = (name for name, record in providers.items() if record["address"] == address)
            if symbol == TAG_LOOKUP:
                id_ = component_id(arg0)
                (matched,) = rpc(f"tag {id_} {arg1}")
                outcome = PARAMETERS + 0x100 * int(matched) if int(matched) else 0
            elif symbol == RESET:
                assert mode == "copy" and get(OBJECT + 4) == component(case["source"])
                id_ = (arg0 - PARAMETERS) // 0x100
                trace.extend(rpc(f"reset {id_} {arg1}"))
                outcome = 0
            elif symbol == VALUE:
                id_ = (arg0 - PARAMETERS) // 0x100
                value, *events = rpc(f"value {id_}")
                trace.extend(events)
                outcome = int(value)
            else:
                assert symbol == RESIZE and arg0 == OUTPUT
                success, capacity = map(int, rpc(f"resize {arg1}"))
                outcome = success
                if success:
                    put(OUTPUT + 12, capacity)
            calls.append([symbol, arm.reg_read(UC_ARM_REG_LR) - 4, arg0, arg1, outcome])
            arm.reg_write(UC_ARM_REG_R0, outcome)
            arm.reg_write(UC_ARM_REG_PC, arm.reg_read(UC_ARM_REG_LR))

        for reg, value in [
            (UC_ARM_REG_R0, OBJECT),
            (UC_ARM_REG_R1, component(case["source"]) if mode == "copy" else OUTPUT),
            (UC_ARM_REG_LR, STOP), (UC_ARM_REG_SP, STACK + 0x8000),
        ]:
            uc.reg_write(reg, value)
        uc.hook_add(UC_HOOK_CODE, hook)
        uc.hook_add(UC_HOOK_MEM_WRITE, lambda arm, access, address, size, value, data:
                    writes.append([address, size, value]) if address < STACK else None)
        uc.emu_start(bodies[0][0]["address"], STOP, count=100000)
        assert uc.reg_read(UC_ARM_REG_PC) == STOP
        if mode == "copy":
            expected = [str(component_id(get(OBJECT + 4))), *rpc("values"), *trace]
            assert writes == [[OBJECT + 4, 4, component(case["source"])]]
        else:
            expected = [
                *(str(component_id(get(ITEMS + index * 4)))
                  for index in range(get(OUTPUT + 8))), "|", *trace,
            ]
            assert all(address == OUTPUT + 8 or ITEMS <= address < ITEMS + 256
                       for address, _, _ in writes)
        process.stdin.close()
        assert process.wait(timeout=5) == 0
    return dict(inputs=case, expected=expected, calls=calls, memory_writes=writes,
                executed_instructions=dict(executed))


def generate(executable, mode):
    original, bodies, providers = read_image(mode)
    return dict(
        original=original, oracle="Unicorn ARM and typed pinned CCL provider RPC",
        unicorn_version=unicorn.__version__,
        executed_ranges=[record for record, _ in bodies], providers=providers,
        cases=[observe(executable, mode, case, bodies, providers) for case in inputs(mode)],
    )


if __name__ == "__main__":
    mode, executable, output = sys.argv[1:]
    Path(output).write_text(json.dumps(generate(Path(executable).resolve(), mode), indent=2) + "\n")
