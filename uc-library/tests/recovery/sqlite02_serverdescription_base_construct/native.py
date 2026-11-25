import hashlib
import json
from pathlib import Path
import sys

from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0
from unicorn.arm_const import UC_ARM_REG_R1, UC_ARM_REG_SP

here = Path(__file__).resolve().parent
root = here.parents[3]
packet = (root / 'temp/recovery-work/rolling-c001-20261124/packeting/sqlite-cycle02'
          / 'serverdescription_worker12/packet/tasks' / here.name / 'CONTEXT.json')
originals = [row['original'] for row in json.loads(packet.read_text())['originals']]
core_name = '_ZN4Core13CStringBufferILi64EEC1EPKc'
STRING_OFFSETS = (8, 0x48, 0x8a, 0xca, 0x10a, 0x14a, 0x18a)
SCALARS = ((0, 4), (4, 4), (0x88, 2), (0x1cc, 4))
BASE, STOP = 0x200000, 0x205000

def oracle(image, original):
    with image.open('rb') as stream:
        elf = ELFFile(stream)
        symtab = elf.get_section_by_name('.symtab')

        def extract(name):
            entry = symtab.get_symbol_by_name(name)[0].entry
            section = elf.get_section(entry.st_shndx)
            start = entry.st_value - section['sh_addr']
            data = section.data()[start:start + entry.st_size]
            return {'mangled': name, 'address': entry.st_value, 'size': entry.st_size,
                    'file_offset': section['sh_offset'] + start, 'section': entry.st_shndx,
                    'sha256': hashlib.sha256(data).hexdigest()}, data

        target, code = extract(original['mangled'])
        address = target['address']
        for field in ('address', 'size', 'file_offset', 'section'):
            assert target[field] == original[field]
        assert code.hex() == original['range_hex']
        assert target['sha256'] == original['range_sha256']
        other_name = original['mangled'].replace('C1Ev', 'C2Ev') if 'C1Ev' in original['mangled'] else original['mangled'].replace('C2Ev', 'C1Ev')
        other, other_code = extract(other_name)
        assert other['address'] != address
        assert other_code != code

        core_address = symtab.get_symbol_by_name(core_name)[0].entry.st_value
        reader_names = (
            '_ZN8Presonus2UC15NetworkListener6notifyERKNS0_17MessageAttributesE',
            '_ZNK8Presonus2UC20NetworkClientManager13getServerTypeERKNS0_17ServerDescriptionE',
            '_ZN8Presonus2UC11NetworkItem13acquireAccessEv',
            '_ZN8Presonus2UC14NetworkManager20getServerContextInfoERNS0_17ServerContextInfoEi',
            '_ZN8Presonus2UC14NetworkManager12setLocalNameEPKc',
            '_ZN8Presonus2UC12RemoteServer14setDescriptionERKNS0_19DiscoveryDescriptorE',
        )
        readers = [extract(name)[0] for name in reader_names]

    def execute(index, poison):
        machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        for page in {address & ~0xfff, core_address & ~0xfff}:
            machine.mem_map(page, 0x1000)
        machine.mem_map(BASE, 0x6000)
        machine.mem_write(address, code)
        receiver = BASE + 0x400 * index
        initial = bytes([poison]) * 0x1d4
        machine.mem_write(receiver, initial)
        machine.reg_write(UC_ARM_REG_SP, 0x204ff0)
        machine.reg_write(UC_ARM_REG_LR, STOP)
        machine.reg_write(UC_ARM_REG_R0, receiver)
        machine.reg_write(UC_ARM_REG_R1, 0xeeeeeeee)
        events = []

        def calls(emu, pc, size, data):
            if pc == core_address:
                offset = emu.reg_read(UC_ARM_REG_R0) - receiver
                arg = emu.reg_read(UC_ARM_REG_R1)
                events.append(['cstring64_c1', offset, arg])
                # Call boundary only. Core behavior is independently provided
                # by the genuine pinned source in portable replay.
                emu.reg_write(UC_ARM_REG_PC, emu.reg_read(UC_ARM_REG_LR))

        def writes(emu, access, where, size, value, data):
            if receiver <= where < receiver + len(initial):
                events.append(['write', where - receiver, size, value])

        machine.hook_add(UC_HOOK_CODE, calls)
        machine.hook_add(UC_HOOK_MEM_WRITE, writes)
        machine.emu_start(address, STOP, count=400)
        assert machine.reg_read(UC_ARM_REG_PC) == STOP
        assert machine.reg_read(UC_ARM_REG_R0) == receiver
        expected = [['write', offset, size, 0] for offset, size in SCALARS[:2]]
        expected += [['cstring64_c1', offset, 0] for offset in STRING_OFFSETS[:2]]
        expected += [['write', SCALARS[2][0], SCALARS[2][1], 0]]
        expected += [['cstring64_c1', offset, 0] for offset in STRING_OFFSETS[2:]]
        expected += [['write', SCALARS[3][0], SCALARS[3][1], 0]]
        assert events == expected, events
        actual = bytes(machine.mem_read(receiver, len(initial)))
        scalar_bytes = {n for offset, size in SCALARS for n in range(offset, offset + size)}
        assert all(actual[n] == (0 if n in scalar_bytes else poison) for n in range(len(initial)))
        values = [int.from_bytes(actual[offset:offset + size], 'little') for offset, size in SCALARS]
        return {'placement': index, 'poison': poison, 'scalar_values': values,
                'receiver_return': True, 'constructor_calls': events}

    cases = [execute(index, poison) for index, poison in enumerate((0x53, 0x99, 0xe2))]
    return {'original': original, 'other_variant': other, 'native_body_alias': False,
            'core_boundary': {'mangled': core_name, 'address': core_address},
            'app_reader_ranges': readers, 'cases': cases}

observed = []
for original in originals:
    image = next(p / original['elf_path'] for p in (root, *root.parents)
                 if (p / original['elf_path']).is_file())
    assert hashlib.sha256(image.read_bytes()).hexdigest() == original['elf']
    observed.append(oracle(image, original))
rendered = json.dumps({'unicorn': unicorn.__version__, 'observations': observed}, indent=2) + '\n'
if len(sys.argv) > 1:
    assert Path(sys.argv[1]).read_text() == rendered
    print(f'Original ServerDescription: {sum(len(outcome["cases"]) for outcome in observed)} executions')
else:
    print(rendered, end='')
