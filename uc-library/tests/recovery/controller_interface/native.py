"""Execute each original application range, with no external-call replacements."""
import hashlib, json, random, struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_HOOK_MEM_READ
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC
ELF = Path('rootfs/RML16AI_Rack_13731/home/root/mixer')
HASH = '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
def generate():
    assert hashlib.sha256(ELF.read_bytes()).hexdigest() == HASH
    rng = random.Random(173)
    cases = [dict(type=t, size=s, iid=i, mode=m, seed=rng.randrange(256)) for t in (0, 0x49466163, -1, 1399157877) for s in (0, 8, 24, -1) for i in (0, 123) for m in (0, 1)]
    ranges = []
    with ELF.open('rb') as f:
        elf = ELFFile(f)
        section = elf.get_section(12)
        for address, name in ((738432, '_ZN8Presonus3Dsp10Controller11getPropertyERN4Core8PropertyE'), (731276, '_ZN8Presonus3Dsp10Controller11processIdleEv')):
            symbol = elf.get_section_by_name('.symtab').get_symbol_by_name(name)[0]
            assert symbol['st_value'] == address and symbol['st_size'] == 16 and symbol['st_shndx'] == 12
            offset = section['sh_offset'] + address - section['sh_addr']
            f.seek(offset); body = f.read(16)
            assert hashlib.sha256(body).hexdigest() == '60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad'
            observations = []
            for c in cases:
                u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
                u.mem_map(address & ~4095, 4096)
                u.mem_write(address, body)
                u.mem_map(0x1000000, 0x10000); u.mem_map(0x2000000, 0x10000)
                state = bytes(rng.getrandbits(8) for _ in range(256))
                payload = bytes([c['seed']] * 32)
                prop = struct.pack('<iiiI', c['type'], c['size'], c['iid'], 0x1000200 if c['mode'] else 0)
                u.mem_write(0x1000000, state); u.mem_write(0x1000100, prop); u.mem_write(0x1000200, payload)
                u.reg_write(UC_ARM_REG_R0, 0x1000000); u.reg_write(UC_ARM_REG_R1, 0x1000100)
                u.reg_write(UC_ARM_REG_SP, 0x2008000); u.reg_write(UC_ARM_REG_LR, 0x1008000)
                writes = []; instructions = []; reads = []
                u.hook_add(UC_HOOK_MEM_WRITE, lambda uc, access, addr, size, value, unused: writes.append([addr, size, value]))
                u.hook_add(UC_HOOK_MEM_READ, lambda uc, access, addr, size, value, unused: reads.append([addr, size]))
                u.hook_add(UC_HOOK_CODE, lambda uc, addr, size, unused: instructions.append(addr))
                u.emu_start(address, 0x1008000, count=10)
                assert u.reg_read(UC_ARM_REG_PC) == 0x1008000
                assert bytes(u.mem_read(0x1000000, 256)) == state
                assert bytes(u.mem_read(0x1000100, 16)) == prop
                assert bytes(u.mem_read(0x1000200, 32)) == payload
                assert all(0x2007ff0 <= w[0] < 0x2008000 for w in writes)
                assert all(0x2007ff0 <= r[0] < 0x2008000 for r in reads)
                assert instructions == list(range(address, address+16, 4))
                observations.append(dict(application_writes=[], external_calls=[], stack_writes=writes, stack_reads=reads, application_reads=[], executed=instructions, state_sha256=hashlib.sha256(state).hexdigest(), property_hex=prop.hex(), payload_hex=payload.hex(), unchanged=True))
            ranges.append(dict(mangled=name, address=address, size=16, section=12, file_offset=offset, sha256=hashlib.sha256(body).hexdigest(), observations=observations))
    return dict(elf_sha256=HASH, unicorn_version=unicorn.__version__, cases=cases, ranges=ranges, return_declarations='Unchanged r0 is not evidence of an original return declaration.')
if __name__ == '__main__':
    import sys
    Path(sys.argv[1]).write_text(json.dumps(generate(), indent=2)+'\n')
