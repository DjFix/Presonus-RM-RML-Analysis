"""Execute each exact ControlRegistrar original with a synthetic live receiver."""
import hashlib
import io
import json
from pathlib import Path

from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_PC, UC_ARM_REG_LR, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP

METHOD = 'castTo'
ORIGINS = [{'mangled': '_ZN8Presonus5Panel16ControlRegistrar6castToEi', 'address': 87880, 'size': 48, 'section': 12, 'role': 'client', 'firmware': 'CS18AI surface 13840', 'elf_sha256': '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0', 'elf_path': '/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling-c001-20261124/packeting/next09/snapshot/rootfs/CS18_v13840/home/root/surface', 'file_offset': 55112, 'body_sha256': '5c926c7dcf716129a2003355ceb0ec3efb6486801b00216c722f6d8ac8888d39'}, {'mangled': '_ZN8Presonus5Panel16ControlRegistrar6castToEi', 'address': 345280, 'size': 48, 'section': 12, 'role': 'server', 'firmware': 'RM/RML mixer 13731', 'elf_sha256': '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07', 'elf_path': '/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling-c001-20261124/packeting/next09/snapshot/rootfs/RML16AI_Rack_13731/home/root/mixer', 'file_offset': 312512, 'body_sha256': '5c926c7dcf716129a2003355ceb0ec3efb6486801b00216c722f6d8ac8888d39'}]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def execute(original, body, inputs):
    address = original['address']
    cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    code = address & ~0xfff
    stack, data, stop = 0x100000, 0x200000, 0x900000
    receiver, message = data + 0x100, data + 0x400
    frame = stack + 0x800
    for page in (code, stack, data, stop):
        cpu.mem_map(page, 0x1000)
    cpu.mem_write(address, body)
    initial = bytearray((i * 13 + 5) % 256 for i in range(192))
    raw_message = bytes(inputs[1:]) if METHOD == 'handleVersion' else b'\xa5\x5a\x12\x34'
    if METHOD == 'init':
        initial[0xa0] = inputs[0]
    cpu.mem_write(receiver, bytes(initial))
    cpu.mem_write(message, raw_message)
    for register, value in ((UC_ARM_REG_SP, frame), (UC_ARM_REG_LR, stop),
                            (UC_ARM_REG_R0, receiver), (UC_ARM_REG_R1, inputs[0] & 0xffffffff),
                            (UC_ARM_REG_R2, message)):
        cpu.reg_write(register, value)
    accesses = []

    def record(_cpu, kind, location, size, value, _):
        if not frame - 16 <= location <= frame - size:
            accesses.append((kind, location, size, value))

    cpu.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, record)
    cpu.emu_start(address, stop, count=20)
    assert cpu.reg_read(UC_ARM_REG_PC) == stop and cpu.reg_read(UC_ARM_REG_SP) == frame
    actual = bytes(cpu.mem_read(receiver, len(initial)))
    unchanged_message = bytes(cpu.mem_read(message, len(raw_message))) == raw_message
    assert unchanged_message
    expected_output = []
    if METHOD == 'init':
        assert accesses == [(unicorn.UC_MEM_WRITE, receiver + 0xa0, 1, 1)]
        assert actual[:0xa0] == initial[:0xa0] and actual[0xa1:] == initial[0xa1:]
        expected_output = [actual[0xa0], int(unchanged_message)]
    elif METHOD == 'handleVersion':
        assert [(kind, location, size) for kind, location, size, _ in accesses] == [
            (unicorn.UC_MEM_READ, message + 2, 1), (unicorn.UC_MEM_READ, message + 3, 1),
            (unicorn.UC_MEM_WRITE, receiver + 0xa4, 4)]
        assert actual[:0xa4] == initial[:0xa4] and actual[0xa8:] == initial[0xa8:]
        expected_output = [int.from_bytes(actual[0xa4:0xa8], 'little'), int(unchanged_message)]
    elif METHOD == 'castTo':
        assert actual == initial
        assert accesses and all(kind == unicorn.UC_MEM_READ and address + 40 <= location <= address + 48 - size
                                for kind, location, size, _ in accesses)
        result = cpu.reg_read(UC_ARM_REG_R0)
        assert result in (receiver, 0)
        expected_output = [int(result == receiver), int(unchanged_message)]
    return dict(inputs=inputs, expected=expected_output, accesses=accesses,
                receiver_before=initial.hex(), receiver_after=actual.hex(),
                message=raw_message.hex())


def observe(original):
    data = Path(original['elf_path']).read_bytes()
    assert digest(data) == original['elf_sha256']
    elf = ELFFile(io.BytesIO(data))
    assert elf['e_machine'] == 'EM_ARM' and elf.little_endian and elf.elfclass == 32
    section = elf.get_section(original['section'])
    assert section.name == '.text' and section['sh_type'] == 'SHT_PROGBITS'
    address, size = original['address'], original['size']
    rows = elf.get_section_by_name('.symtab').get_symbol_by_name(original['mangled'])
    matches = [r for r in rows if r['st_value'] == address and r['st_size'] == size
               and r['st_shndx'] == original['section'] and r['st_info']['type'] == 'STT_FUNC']
    assert len(matches) == 1
    relative = address - section['sh_addr']
    offset = section['sh_offset'] + relative
    assert 0 <= relative <= section['sh_size'] - size and offset == original['file_offset']
    body = data[offset:offset+size]
    assert digest(body) == original['body_sha256']
    if METHOD == 'init':
        cases = [[0], [1], [255]]
    elif METHOD == 'handleVersion':
        cases = [[-1, 0x67, 0x0c, 0, 0], [0, 0xff, 0x18, 0xa5, 0x3a],
                 [2147483647, 0, 0, 0xa5, 0x3a], [-2147483648, 0xa5, 0x5a, 0xff, 0xff]]
    else:
        ids = [int.from_bytes(body[at:at+4], 'little') for at in (40, 44)]
        cases = [[i] for i in (ids[0], ids[1], 0, -1, ids[0] - 1, ids[1] + 1)]
    result = dict(original, engine='Unicorn ' + unicorn.__version__, body_hex=body.hex(),
                  cases=[execute(original, body, case) for case in cases])
    return json.loads(json.dumps(result))


def observations():
    return [observe(original) for original in ORIGINS]


if __name__ == '__main__':
    print(json.dumps(observations(), indent=2))
