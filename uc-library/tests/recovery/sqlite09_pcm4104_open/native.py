"""Run original CS18AI PCM4104 entries with offline system boundaries."""
import ctypes
import importlib.util
import itertools
import json
from pathlib import Path
import struct
import sys

helper = Path(__file__).parents[1] / "sqlite_pcm4104_read_register/native.py"
spec = importlib.util.spec_from_file_location("register_oracle", helper)
native = importlib.util.module_from_spec(spec)
sys.dont_write_bytecode = True
spec.loader.exec_module(native)
from unicorn.arm_const import UC_ARM_REG_R4

OPEN, CLOSE, LOG10F = 0xad8c, 0xac30, 0xae10
VFP_HELPERS = {0x187588, 0x1873f0, 0x187150, 0x187798, 0x187854, 0x187768, 0x1876e8}
PATH = native.OUTPUT
FORMAT0 = "SPI: Failed to open PCM4104 SPI port\n"
FLOAT = struct.Struct("<f")


def signed(value):
    return ctypes.c_int32(value).value


def w(value):
    return native.WORD.pack(value & 0xffffffff)


def fbits(value):
    return native.WORD.unpack(FLOAT.pack(value))[0]


def run(uc, mode, original, allowed, args, math=None):
    initial_fd, opened_fd, step, channel, value, gain, mode_byte, response = args
    if mode in ("base_construct", "complete_construct"):
        uc.mem_write(native.OWNER, b"\xcd" * 8)
    else:
        uc.mem_write(native.OWNER, w(initial_fd) + b"\xff" * 4)
    uc.mem_write(PATH, b"pcm4104-offline\0")
    uc.mem_write(native.ERRNO, w(71))
    uc.mem_write(native.STACK - 512, b"\xcd" * 512)
    traces = []
    math_entries = []
    transport = 0

    def cstr(at):
        result = bytearray()
        for i in range(120):
            byte = uc.mem_read(at + i, 1)
            if not byte[0]:
                return result.decode()
            result.extend(byte)
        raise AssertionError("unterminated string")

    def boundary(machine, pc, _size, _data):
        nonlocal transport
        if math and math.is_code(pc):
            return
        if any(start <= pc < end for start, end in allowed):
            return
        read = machine.reg_read
        r0, r1, r2 = [read(r) for r in (native.UC_ARM_REG_R0, native.UC_ARM_REG_R1,
                                         native.UC_ARM_REG_R2)]
        if pc == OPEN:
            state = machine.mem_read(native.OWNER, 8)
            fd = signed(native.WORD.unpack(state[:4])[0])
            traces.append(" ".join(map(str, ("open", cstr(r0), r1, fd, *state[4:]))))
            result = opened_fd
        elif pc == CLOSE:
            traces.append(f"close {signed(r0)}")
            result = -1 if step == 1 else 0
        elif pc == native.IOCTL:
            transport += 1
            if r1 == 0x80016b01:
                traces.append(f"mode {signed(r0)} {r1} {machine.mem_read(r2, 1)[0]}")
                machine.mem_write(r2, bytes([mode_byte]))
            elif r1 == 0x40016b01:
                traces.append(f"mode {signed(r0)} {r1} {machine.mem_read(r2, 1)[0]}")
            else:
                tx, rx, length, *fields = native.DEFINED_TRANSFER.unpack(
                    machine.mem_read(r2, native.DEFINED_TRANSFER.size))
                assert length == 2 and tx != rx
                packet = [signed(r0), r1, length, *fields, *machine.mem_read(tx, length)]
                traces.append("transfer " + " ".join(map(str, packet)))
                machine.mem_write(rx, bytes([response ^ 0xff, response]))
            result = -1 if step == transport else 0
        elif pc == native.ERRNO_LOCATION:
            traces.append("errno")
            result = native.ERRNO
        elif pc == native.DIAGNOSTIC:
            message = cstr(r0)
            traces.append("diagnostic " + (message if message == FORMAT0
                                           else message % signed(r1)).rstrip("\n"))
            result = 0
        elif math and pc == math.errno_entry:
            math_entries.append(["errno"])
            result = native.ERRNO
        else:
            assert math and pc == LOG10F, hex(pc)
            math_entries.append(["log10f", r0])
            machine.reg_write(native.UC_ARM_REG_PC, math.entry)
            return
        if result < 0 and pc in (OPEN, CLOSE, native.IOCTL):
            machine.mem_write(native.ERRNO, w(9 if pc == OPEN else 5))
        machine.reg_write(native.UC_ARM_REG_R0, result & 0xffffffff)
        machine.reg_write(native.UC_ARM_REG_PC, read(native.UC_ARM_REG_LR))

    if mode in ("open", "base_construct", "complete_construct"):
        arg1 = PATH
    else:
        arg1 = channel
    arg2 = gain if mode == "attenuate_channel" else value
    for reg, item in ((native.UC_ARM_REG_R0, native.OWNER), (native.UC_ARM_REG_R1, arg1),
                      (native.UC_ARM_REG_R2, arg2), (UC_ARM_REG_R4, 0),
                      (native.UC_ARM_REG_SP, native.STACK), (native.UC_ARM_REG_LR, native.STOP)):
        uc.reg_write(reg, item & 0xffffffff)
    hook = uc.hook_add(native.UC_HOOK_CODE, boundary)
    uc.emu_start(original["address"], native.STOP, count=12000)
    uc.hook_del(hook)
    assert uc.reg_read(native.UC_ARM_REG_PC) == native.STOP
    ret = uc.reg_read(native.UC_ARM_REG_R0)
    if mode.endswith(("construct", "destroy")):
        assert ret == native.OWNER
        ret = -1
    state = uc.mem_read(native.OWNER, 8)
    traces.append("state " + " ".join(map(str, [
        ret, signed(native.WORD.unpack(state[:4])[0]), *state[4:],
        native.WORD.unpack(uc.mem_read(native.ERRNO, 4))[0]])))
    record = {"args": args, "observed": traces}
    if math:
        record["math_entries"] = math_entries
    return record


def cases(mode):
    if mode in ("open", "base_construct", "complete_construct"):
        return list(itertools.product(
            (0, 23) if mode == "open" else (0,), (-1, 0, 17),
            (0, 1, 2, 3, 6, 9), (0,), (0,), (0,), (0, 3, 0xfb), (37,)))
    if mode.endswith("destroy"):
        return [(fd, 0, step, 0, 0, 0, 0, 77)
                for fd, step in itertools.product((0, 17, 257), (0, 1))]
    if mode == "attenuate_channel":
        gains = [fbits(x) for x in (0., -1., 1e-12, 1e-6, 0.001, 0.1, .5, 1.,
                                    1.995, 2., 6., 1000., float("inf"), float("nan"))]
        return list(itertools.product((0, 17), (0,), (0, 1, 2), (-1, 0, 3, 4),
                                      (0,), gains, (0,), (37,)))
    if mode == "mute_channel":
        return list(itertools.product((0, 17), (0,), (0, 1, 2, 3), (0, 1, 2, 3, 4),
                                      (0, 1), (0,), (0,), (0, 37, 255)))
    if mode == "set_attenuation_value":
        return list(itertools.product((0, 17), (0,), (0, 1, 2), (-2147483648, -1, 0, 3, 4, 2147483647),
                                      (0, 37, 255), (0,), (0,), (37,)))
    return [(fd, 0, step, 0, 0, 0, 0, 37)
            for fd, step in itertools.product((0, 17), range(8))]


def fixtures(context, math=None):
    mode = context.parent.name.removeprefix("sqlite09_pcm4104_")
    original, elf = native.original_image(context)
    uc = native.Uc(native.UC_ARCH_ARM, native.UC_MODE_ARM)
    for segment in elf.iter_segments():
        if segment["p_type"] == "PT_LOAD":
            start = segment["p_vaddr"] & ~4095
            end = (segment["p_vaddr"] + segment["p_memsz"] + 4095) & ~4095
            uc.mem_map(start, end - start)
            uc.mem_write(segment["p_vaddr"], segment.data())
    uc.mem_map(native.OWNER, 0x5000)
    if math:
        math.install(uc)
    names = list(elf.get_section_by_name(".symtab").iter_symbols())
    allowed = {(s["st_value"], s["st_value"] + s["st_size"]) for s in names
               if s["st_info"]["type"] == "STT_FUNC"
               and (s.name.startswith("_ZN8Presonus7PCM410410Pcm4104Spi")
                    or s["st_value"] in VFP_HELPERS)}
    dependencies = {}
    for address, end in sorted(allowed):
        if address not in dependencies:
            payload = bytes(uc.mem_read(address, end - address))
            dependencies[address] = {"address": address, "size": len(payload),
                                     "sha256": native.digest(payload)}
    result = {"mode": mode, "native_execution_ranges": list(dependencies.values()),
              "original": {k: v for k, v in original.items() if k != "range_hex"},
              "cases": [run(uc, mode, original, allowed, args, math) for args in cases(mode)]}
    if math:
        result["math_provider"] = math.metadata
    return result


if __name__ == "__main__":
    print(json.dumps(fixtures(Path(sys.argv[1])), separators=(",", ":")))
