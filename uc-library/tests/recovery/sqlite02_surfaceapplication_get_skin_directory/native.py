"""Verify and execute the original filename value-return wrapper."""
import hashlib
import io
import json
from pathlib import Path
import struct

import capstone
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_SP,
)

TASK = Path(__file__).resolve().parent.name
PACKET = Path('temp/recovery-work/sqlite-issued/packet') / TASK / 'CONTEXT.json'
PROJECT = Path('/home/rs/projects/opencs/ai-line-analysis')
CTOR = '_ZN4Core8Portable8FileNameC1EPKc'
LOAD = '_ZN8Presonus7Surface18SurfaceApplication8loadSkinEv'
LIST = '_ZNK8Presonus7Surface24ChannelInfoPageComponent16getMaxListOffsetENS1_8ListTypeE'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def extract(elf, image, name):
    sym, = elf.get_section_by_name('.symtab').get_symbol_by_name(name)
    assert sym['st_info']['type'] == 'STT_FUNC'
    section = elf.get_section(sym['st_shndx'])
    start = sym['st_value'] - section['sh_addr']
    size = sym['st_size']
    assert 0 <= start < start + size <= section['sh_size']
    data = section.data()[start:start + size]
    offset = section['sh_offset'] + start
    assert image[offset:offset + size] == data
    return dict(mangled=name, address=sym['st_value'], size=size,
                section=sym['st_shndx'], section_name=section.name,
                file_offset=offset, range_sha256=digest(data), range_hex=data.hex())


def execute(target, ctor_pc, copy_pc, literal, seed):
    entry = target['address']
    literal_address = literal['address']
    result = 0x10000100 + 0x100 * seed
    stack, finish = 0x20000800, 0x30000000
    machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    code_pages = {address & ~0xfff for address in
                  (entry, ctor_pc, copy_pc, literal_address, result, stack, finish)}
    for page in code_pages:
        machine.mem_map(page, 0x1000)
    machine.mem_write(entry, bytes.fromhex(target['range_hex']))
    machine.mem_write(literal_address, bytes.fromhex(literal['hex']))
    for stub in (ctor_pc, copy_pc):
        machine.mem_write(stub, bytes.fromhex('1eff2fe1'))  # bx lr
    guard = bytes([0xCA + seed]) * 272
    machine.mem_write(result - 8, guard)
    machine.mem_write(stack - 512, bytes([0x30 + seed]) * 512)
    machine.reg_write(UC_ARM_REG_R0, result)
    # No receiver is supplied. The independent call sites also assign only
    # the hidden result register; an unmapped stale r1 must be harmless.
    machine.reg_write(UC_ARM_REG_R1, 0x60000000 + seed)
    machine.reg_write(UC_ARM_REG_SP, stack)
    machine.reg_write(UC_ARM_REG_LR, finish)
    calls = []
    value_bytes = None

    def hook(_, pc, __, ___):
        nonlocal value_bytes
        if pc not in (ctor_pc, copy_pc):
            return
        dest = machine.reg_read(UC_ARM_REG_R0)
        arg = machine.reg_read(UC_ARM_REG_R1)
        if pc == ctor_pc:
            if not calls:
                assert dest == result and arg == 0
                machine.mem_write(dest, b'\0')
            else:
                assert stack - 512 <= dest and dest + 256 <= stack
                assert arg == literal_address
                # Bounded constructor seam. The path prefix comes from the
                # mapped ELF literal. Preserve the distinct tail canary so a
                # short copy cannot pass.
                machine.mem_write(dest, bytes(machine.mem_read(arg, literal['size'])))
                value_bytes = bytes(machine.mem_read(dest, 256))
            calls.append(['filename_ctor', pc, dest, arg])
        else:
            count = machine.reg_read(UC_ARM_REG_R2)
            assert dest == result and arg == calls[-1][2] and count == 256
            machine.mem_write(dest, bytes(machine.mem_read(arg, count)))
            calls.append(['memcpy', pc, dest, arg, count])

    machine.hook_add(UC_HOOK_CODE, hook)
    machine.emu_start(entry, finish, count=60)
    assert machine.reg_read(UC_ARM_REG_PC) == finish
    assert machine.reg_read(UC_ARM_REG_SP) == stack
    assert machine.reg_read(UC_ARM_REG_R0) == result
    assert [call[0] for call in calls] == ['filename_ctor', 'filename_ctor', 'memcpy']
    assert machine.mem_read(result - 8, 272) == guard[:8] + value_bytes + guard[-8:]
    return dict(return_storage=result, returned_storage=result, calls=calls,
                value=value_bytes.split(b'\0', 1)[0].decode('ascii'),
                copied_bytes_sha256=digest(value_bytes))


def observe():
    packet = json.loads(PACKET.read_text())
    target = packet['originals'][0]['original']
    binary = Path(target['elf_path'])
    if not binary.is_file():
        binary = PROJECT / binary
    image = binary.read_bytes()
    assert digest(image) == target['elf']
    elf = ELFFile(io.BytesIO(image))
    assert elf['e_machine'] == 'EM_ARM' and elf.little_endian
    verified = extract(elf, image, target['mangled'])
    assert all(target[key] == value for key, value in verified.items())
    ctor = extract(elf, image, CTOR)
    relocations = elf.get_section_by_name('.rel.plt')
    dynsym = elf.get_section(relocations['sh_link'])
    memcpy, = [dynsym.get_symbol(rel['r_info_sym'])
               for rel in relocations.iter_relocations()
               if dynsym.get_symbol(rel['r_info_sym']).name == 'memcpy']
    plt = elf.get_section_by_name('.plt')
    copy_pc = memcpy['st_value']
    assert plt['sh_addr'] <= copy_pc < plt['sh_addr'] + plt['sh_size']

    code = bytes.fromhex(target['range_hex'])
    literal_address, = struct.unpack_from('<I', code, len(code) - 4)
    offset, = elf.address_offsets(literal_address)
    literal = image[offset:offset + 12]
    assert literal == b'/media/skin\0'
    mapped = dict(address=literal_address, file_offset=offset,
                  size=len(literal), hex=literal.hex())

    decoder = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
    callers = []
    for name in (LOAD, LIST):
        caller = extract(elf, image, name)
        instructions = list(decoder.disasm_lite(bytes.fromhex(caller['range_hex']),
                                                caller['address']))
        for index, (_, _, operation, param) in enumerate(instructions):
            if operation == 'bl' and int(param.removeprefix('#'), 16) == target['address']:
                window = [list(row) for row in instructions[index - 3:index + 1]]
                assert window[-2][2] == 'mov' and window[-2][3].startswith('r0, ')
                callers.append(dict(mangled=name, range_sha256=caller['range_sha256'],
                                    address=window[-1][0], instructions=window))
    assert len(callers) == 3
    cases = [execute(target, ctor['address'], copy_pc, mapped, i) for i in range(2)]
    return dict(original=target, constructor_boundary=ctor,
                copy_boundary=dict(name='memcpy', plt_address=copy_pc),
                mapped_literal=mapped, direct_callers=callers, cases=cases)


if __name__ == '__main__':
    print(json.dumps(observe(), indent=2))
