"""Offline original ARM observations only; no reconstructed C++ expected values."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import random
import time

from elftools.elf.elffile import ELFFile
import unicorn
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP, UC_ARM_REG_LR


def main():
    started = time.time()
    parser = argparse.ArgumentParser()
    parser.add_argument('--elf', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[4]
    target = {'original_elf_sha256': '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07', 'mangled': '_ZN8Presonus5Panel8MixerLCD14setAltKeyParamEPN4Core8Portable9ParameterE', 'address': 395712, 'size': 20, 'section': 12, 'firmware': 'RM/RML mixer 13731', 'role': 'server'}
    preflight = {'binary': {'path': args.elf}, 'range': {'file_offset': 362944, 'bytes_sha256': '928fb94e9606063857d12d8e693b998c409efc326543b9ba069c4bad88ea4dfc'}}
    binary = root / preflight['binary']['path']
    raw = binary.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == target['original_elf_sha256']
    elf = ELFFile(io.BytesIO(raw))
    section = elf.get_section(target['section'])
    offset = section['sh_offset'] + target['address'] - section['sh_addr']
    code = raw[offset:offset + target['size']]
    assert offset == preflight['range']['file_offset']
    assert hashlib.sha256(code).hexdigest() == preflight['range']['bytes_sha256']
    assert target['size'] == 20
    rng = random.Random(20261113)
    pointers = [0, 1, 0xffffffff, 0x80000000, 0x00300000, 0x00300110]
    pointers += [rng.getrandbits(32) for _ in range(128)]
    observations = []
    for index, pointer in enumerate(pointers):
        machine = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM | unicorn.UC_MODE_LITTLE_ENDIAN)
        machine.mem_map(target['address'] & ~4095, 4096)
        machine.mem_write(target['address'], code)
        machine.mem_map(0x200000, 0x10000)
        machine.mem_map(0x300000, 4096)
        machine.mem_map(0x100000, 4096)
        before = bytes(rng.getrandbits(8) for _ in range(512))
        machine.mem_write(0x300000, before)
        machine.reg_write(UC_ARM_REG_R0, 0x300000)
        machine.reg_write(UC_ARM_REG_R1, pointer)
        machine.reg_write(UC_ARM_REG_SP, 0x20f000)
        machine.reg_write(UC_ARM_REG_LR, 0x100000)
        trace, writes = [], []
        machine.hook_add(unicorn.UC_HOOK_CODE, lambda uc, address, size, data: trace.append(address))
        machine.hook_add(unicorn.UC_HOOK_MEM_WRITE,
                         lambda uc, access, address, size, value, data: writes.append(
                             {'address': address, 'size': size, 'value': value}))
        machine.emu_start(target['address'], 0x100000, count=32)
        after = bytes(machine.mem_read(0x300000, 512))
        assert trace == list(range(target['address'], target['address'] + 20, 4))
        assert machine.reg_read(UC_ARM_REG_SP) == 0x20f000
        object_writes = [w for w in writes if 0x300000 <= w['address'] < 0x301000]
        assert len(object_writes) == 1 and object_writes[0]['address'] == 0x300110 and object_writes[0]['size'] == 4
        assert before[:0x110] == after[:0x110] and before[0x114:] == after[0x114:]
        observations.append({'case': index, 'input_r1': pointer, 'observed_stored_bytes': after[0x110:0x114].hex(),
            'portable_case': 0 if pointer == 0 else 1 + index % 2, 'object_writes': object_writes, 'all_writes': writes, 'trace': trace,
            'before_object_sha256': hashlib.sha256(before).hexdigest(),
            'after_object_sha256': hashlib.sha256(after).hexdigest(), 'surrounding_memory_unchanged': True,
            'returned_r0': machine.reg_read(UC_ARM_REG_R0), 'stack_restored': True})
    output = {'producer': {'path': str(Path(__file__).relative_to(root)),
        'sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        'original': target, 'original_file_offset': offset, 'original_bytes_sha256': hashlib.sha256(code).hexdigest(),
        'unicorn_version': unicorn.__version__, 'started_epoch': started, 'finished_epoch': time.time(),
        'cases': len(observations), 'observations': observations,
        'limitations': 'Original five ARM instructions executed in isolated memory. Pointer values are stored, never dereferenced. No hardware/syscalls/Core binary execution. Returned r0 observation does not establish original C++ return declaration. This is native evidence only, not reconstructed C++ or readiness.'}
    with Path(args.output).open('x') as stream:
        stream.write(json.dumps(output, indent=2) + '\n')
    print(json.dumps({'native_cases': len(observations), 'seconds': time.time() - started, 'readiness': False}))


if __name__ == '__main__':
    main()
