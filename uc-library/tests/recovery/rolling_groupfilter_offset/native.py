"""Execute the selected app instruction range in an isolated ARM emulator."""
import hashlib
import itertools
import struct
from pathlib import Path

from elftools import __version__ as elf_version
from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc
from unicorn import __version__ as unicorn_version
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP

TASK = Path(__file__).parent.name
METHOD = {
    'rolling_c001_85068a5a0676e789': 'count',
    'rolling_groupfilter_visible': 'visible',
    'rolling_groupfilter_offset': 'getChannelOffset',
}[TASK]
SUFFIX = {'count': '5countEv', 'visible': '7visibleEi', 'getChannelOffset': '16getChannelOffsetEi'}[METHOD]
MANGLED = '_ZNK8Presonus18ChannelGroupFilter' + SUFFIX
FROZEN = Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling-c001-20261124/packeting/next09/snapshot')
RELEASES = (
    ('client', 'CS18AI surface 13840', 'rootfs/CS18_v13840/home/root/surface',
     '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'),
    ('server', 'RM/RML mixer 13731', 'rootfs/RML16AI_Rack_13731/home/root/mixer',
     '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'),
)
RANGE_HASHES = {
    'count': ('f0e5b61d4c9de5cd49dabf60a4184953ad40a736012f13236bb77b7e2299b3e6',) * 2,
    'visible': ('e5837b1fa6213c62918ef74a9107406cd941e75b67f66acf86ef5ef53d1823dd',
                'b3dd9dd012fe70a904a81b6854023d60b50c727682032a34bd1ca48445f251ed'),
    'getChannelOffset': ('d2b1b4d3a11600fa8815292ed6f34eaf2d3e57ec83aaaad30fd8ebd545134047',) * 2,
}
OBJECT, ITEMS, STOP, STACK = 0x1000000, 0x1001000, 0x1002000, 0x1004000


def digest(data):
    return hashlib.sha256(data).hexdigest()


def cases():
    masks = ([], [0], [1], [0, 1, 0, 1], [0] * 6,
             [1] * 5, [0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0])
    for items in masks:
        if METHOD == 'count':
            yield [items, 0, 0]
        elif METHOD == 'visible':
            for index, error in itertools.product(range(-2, len(items) + 2), (0, 1)):
                yield [items, index, error]
        else:
            for index in [-2147483648, -1, *range(len(items) + 2), 2147483647]:
                yield [items, index, 0]


def execute(original, code, error_slot, case):
    items, index, error = case
    capacity = ((len(items) + 4) // 5) * 5
    start = original['address']
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    page = start & ~0xfff
    uc.mem_map(page, 0x2000)
    uc.mem_write(start, code)
    uc.mem_map(OBJECT, 0x4000)
    if error_slot is not None:
        uc.mem_map(error_slot & ~0xfff, 0x1000)
        uc.mem_write(error_slot, bytes([error]))
    uc.mem_write(OBJECT, struct.pack('<4I', 0, ITEMS, len(items), capacity))
    if capacity:
        uc.mem_write(ITEMS, bytes(items).ljust(capacity, b'\0'))

    def code_guard(_uc, address, size, _data):
        assert start <= address < start + len(code), (address, size)

    def write_guard(_uc, _access, address, size, _value, _data):
        assert STACK - 32 <= address < address + size <= STACK, (address, size)

    uc.hook_add(UC_HOOK_CODE, code_guard)
    uc.hook_add(UC_HOOK_MEM_WRITE, write_guard)
    for register, value in ((UC_ARM_REG_R0, OBJECT), (UC_ARM_REG_R1, index),
                            (UC_ARM_REG_SP, STACK), (UC_ARM_REG_LR, STOP)):
        uc.reg_write(register, value & 0xffffffff)
    uc.emu_start(start, STOP, count=256)
    assert uc.reg_read(UC_ARM_REG_PC) == STOP
    return {'input': case, 'capacity': capacity, 'result': uc.reg_read(UC_ARM_REG_R0),
            'external_memory_writes': 0, 'external_calls': 0}


def observe():
    observations = []
    for firmware_row, target_hash in zip(RELEASES, RANGE_HASHES[METHOD]):
        role, firmware, name, elf_sha = firmware_row
        path = FROZEN / name
        raw = path.read_bytes()
        assert digest(raw) == elf_sha
        with path.open('rb') as stream:
            elf = ELFFile(stream)
            symbols = elf.get_section_by_name('.symtab')
            symbol, = symbols.get_symbol_by_name(MANGLED)
            address, size = symbol['st_value'], symbol['st_size']
            section = elf.get_section(symbol['st_shndx'])
            relative = address - section['sh_addr']
            assert symbol['st_info']['type'] == 'STT_FUNC'
            assert section.name == '.text' and 0 <= relative <= section['sh_size'] - size
            offset = section['sh_offset'] + relative
            code = raw[offset:offset + size]
            assert digest(code) == target_hash
            error_slot = None
            if METHOD == 'visible':
                error, = symbols.get_symbol_by_name('_ZN4Core11ConstVectorIbE5errorE')
                error_slot = error['st_value']
                assert elf.get_section(error['st_shndx'])['sh_type'] == 'SHT_NOBITS'
                assert error_slot == struct.unpack_from('<I', code, size - 4)[0]
        original = dict(role=role, firmware=firmware, elf_sha256=elf_sha, mangled=MANGLED,
                        address=address, size=size, section=section.name)
        observations.append(dict(original=original, path=str(path), file_offset=offset,
                                 range_sha256=target_hash, error_slot=error_slot,
                                 cases=[execute(original, code, error_slot, case) for case in cases()]))
    return dict(method=METHOD, unicorn_version=unicorn_version, pyelftools_version=elf_version,
                observations=observations)
