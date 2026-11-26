"""Run original ARM D0 with the firmware libc allocator and libstdc++ delete."""
import hashlib
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_INTR
from unicorn.arm_const import (UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0,
                               UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
                               UC_ARM_REG_R7, UC_ARM_REG_SP)

TASK = Path(__file__).parent.name
PACKET = Path('temp/recovery-work/sqlite-issued/packet') / TASK / 'CONTEXT.json'
ROOT = Path('/home/rs/projects/opencs/ai-line-analysis')
FW = ROOT / 'rootfs/CS18_v13840'
LIBC = FW / 'lib/libc-2.9.so'
STDCXX = FW / 'usr/lib/libstdc++.so.6.0.10'
LOADER = FW / 'lib/ld-2.9.so'
ELF = FW / 'home/root/surface'
REGISTERS = (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)
STACK, EXIT, HEAP = 0x31010000, 0x31020000, 0x32000000


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Image:
    def __init__(self, path, base, cpu):
        self.path, self.base = path, base
        self.file = path.open('rb')
        self.elf = ELFFile(self.file)
        self.tables = [self.elf.get_section_by_name(n) for n in ('.symtab', '.dynsym')]
        loads = [s for s in self.elf.iter_segments() if s['p_type'] == 'PT_LOAD']
        start = min(s['p_vaddr'] for s in loads) & ~4095
        end = (max(s['p_vaddr'] + s['p_memsz'] for s in loads) + 4095) & ~4095
        cpu.mem_map(base + start, end - start)
        for s in loads:
            cpu.mem_write(base + s['p_vaddr'], s.data())

    def symbols(self, name):
        return [s for table in self.tables if table is not None
                for s in table.get_symbol_by_name(name) or []
                if s['st_shndx'] != 'SHN_UNDEF']

    def address(self, name):
        return self.base + self.symbols(name)[0]['st_value']

    def range(self, name):
        s = next(s for s in self.symbols(name) if s['st_size'])
        sec = self.elf.get_section(s['st_shndx'])
        offset = s['st_value'] - sec['sh_addr']
        body = sec.data()[offset:offset+s['st_size']]
        return dict(mangled=name, address=s['st_value'], size=s['st_size'],
                    section=s['st_shndx'], section_name=sec.name,
                    file_offset=sec['sh_offset']+offset, range_hex=body.hex(),
                    range_sha256=hashlib.sha256(body).hexdigest())


def observe():
    packet = json.loads(PACKET.read_text())
    target, = packet['originals']
    target = target['original']
    assert sha(ELF) == target['elf']
    for entry in packet['task']['review']['evidence'] + packet['task']['review']['providers']:
        assert sha(Path(entry['path'])) == entry['sha256'], entry
    cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    exe = Image(ELF, 0, cpu)
    libc = Image(LIBC, 0x10000000, cpu)
    cxx = Image(STDCXX, 0x11000000, cpu)
    loader = Image(LOADER, 0x12000000, cpu)
    images = [exe, cxx, libc, loader]
    original = exe.range(target['mangled'])
    assert all(original[key] == target[key] for key in original)
    cpu.mem_map(STACK - 0x10000, 0x21000)
    cpu.mem_map(HEAP, 0x200000)
    cpu.mem_map(0xffff0000, 0x1000)
    cpu.mem_write(0xffff0fe0, struct.pack("<I", 0xe12fff1e))  # kuser return

    def read(addr):
        return struct.unpack('<I', cpu.mem_read(addr, 4))[0]

    def put(addr, value):
        cpu.mem_write(addr, struct.pack('<I', value & 0xffffffff))

    # Dynamic relocations for the bounded allocator and destructor paths.
    for image in images:
        for name in ('.rel.dyn', '.rel.plt'):
            rel = image.elf.get_section_by_name(name)
            if rel is None:
                continue
            syms = image.elf.get_section(rel['sh_link'])
            for r in rel.iter_relocations():
                addr = image.base + r['r_offset']
                t = r['r_info_type']
                if t == 23:
                    put(addr, image.base + read(addr))
                    continue
                if t in (2, 21, 22):
                    symbol = syms.get_symbol(r['r_info_sym'])
                    bind = next((i.address(symbol.name) for i in images
                                 if i.symbols(symbol.name)), 0)
                    put(addr, bind + (read(addr) if t == 2 else 0))

    # Model the loader's empty link-map lookup during malloc initialization.
    # Both the allocator code and the resulting arena initialization execute.
    lookup = libc.base + 0xfa298
    brk = HEAP
    syscalls = []

    def interrupt(uc, intno, _):
        nonlocal brk
        syscall = uc.reg_read(UC_ARM_REG_R7)
        arg = uc.reg_read(UC_ARM_REG_R0)
        syscalls.append([intno, syscall, arg])
        if syscall == 45:  # Linux brk, with fixed emulator heap mapping.
            if HEAP <= arg < HEAP + 0x200000:
                brk = arg
            uc.reg_write(UC_ARM_REG_R0, brk)
        else:
            raise RuntimeError(f'unmodeled syscall {syscall} at {hex(uc.reg_read(UC_ARM_REG_PC))}')

    cpu.hook_add(UC_HOOK_INTR, interrupt)
    component_ctor = '_ZN4Core8Portable9ComponentC1EPKc'
    component_dtor = '_ZN4Core8Portable9ComponentD2Ev'
    captured = {exe.address(component_dtor): 'component_D2',
                cxx.address('_ZdlPv'): 'operator_delete',
                libc.address('__libc_free'): 'libc_free',
                libc.address('__libc_malloc'): 'libc_malloc'}
    calls = []
    latest = []

    def trace(uc, address, size, _):
        if address == 0xffff0fe0:
            uc.reg_write(UC_ARM_REG_R0, STACK + 0x2000)
            return
        if address == lookup:
            uc.reg_write(UC_ARM_REG_R0, 0)
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
            return
        latest.append(address)
        if len(latest) > 100:
            latest.pop(0)
        if address in captured:
            calls.append([captured[address], uc.reg_read(UC_ARM_REG_R0)])

    cpu.hook_add(UC_HOOK_CODE, trace)

    def call(entry, *args):
        for r, a in zip(REGISTERS, args):
            cpu.reg_write(r, a)
        cpu.reg_write(UC_ARM_REG_SP, STACK)
        cpu.reg_write(UC_ARM_REG_LR, EXIT)
        try:
            cpu.emu_start(entry, EXIT, count=200000)
        except Exception as exc:
            raise RuntimeError(f'entry {hex(entry)} recent {list(map(hex, latest))}, '
                               f'pc {hex(cpu.reg_read(UC_ARM_REG_PC))}, syscalls {syscalls}') from exc
        assert cpu.reg_read(UC_ARM_REG_PC) == EXIT
        return cpu.reg_read(UC_ARM_REG_R0)

    malloc = libc.address('__libc_malloc')
    add_params = '_ZN4Core8Portable9ParamList3addEPKNS0_9ParamInfoEib'
    page_base = '_ZN8Presonus13PageComponentC2EPKcS2_i'
    get_param = '_ZNK4Core8Portable9Component17getParameterByTagEi'
    add_child = '_ZN4Core8Portable9Component8addChildEPS1_'
    dtor_prefix = '_ZN8Presonus7Surface18DawFxPageComponentD'
    destructors = {kind: exe.range(dtor_prefix + kind + 'Ev') for kind in ('1', '0')}

    def cstr(addr):
        result = bytearray()
        while (byte := cpu.mem_read(addr + len(result), 1)[0]):
            result.append(byte)
            assert len(result) < 64
        return result.decode()

    descriptors = []
    base = []

    def descriptors_at_entry(_, _pc, _width, _context):
        owner, addr, count, owns = [cpu.reg_read(r) for r in REGISTERS]
        assert count in (6, 7)
        descriptors.append([bool(owns), [
            bytes(cpu.mem_read(addr+84*i, 84)).hex() for i in range(count)]])

    def page_at_entry(_, _pc, _width, _context):
        _, name, form, tag = [cpu.reg_read(r) for r in REGISTERS]
        base.append([cstr(name), cstr(form), tag])

    for name, hook in ((add_params, descriptors_at_entry), (page_base, page_at_entry)):
        entry = exe.address(name)
        cpu.hook_add(UC_HOOK_CODE, hook, begin=entry, end=entry)

    def scalar_rows():
        for owns, rows in descriptors:
            for h in rows:
                kind, tag, name, lo, hi, mid, default, delta, flags, *ptr = struct.unpack(
                    '<ii32s5fi5I', bytes.fromhex(h))
                yield [kind, tag, name.rstrip(b'\0').decode(), lo, hi, mid,
                       default, delta, flags, int(any(ptr)), int(owns)]

    def make_page(form, tag):
        addr = STACK + 0x4000
        cpu.mem_write(addr, form.encode() + b'\0')
        page = call(malloc, 0xe0)
        descriptors.clear()
        base.clear()
        call(original['address'], page, addr, tag)
        assert base == [['dawFx', form, tag]]
        assert [len(rows) for _, rows in descriptors] == [7, 7, 7, 7, 7, 6]
        mode = call(exe.address(get_param), page, 1000)
        assert mode != 0 and mode == read(page + 0xc0)
        state = [read(page + field) for field in (0xb8, 0xbc, 0xc4, 0xc8)]
        assert state == [0, 0, 0, 0]
        return page, dict(base=base[0], state=state, modes_bound=int(mode != 0),
                          descriptors=list(scalar_rows()), blocks=descriptors[:])

    cases = []
    for kind, form, tag in [('1', 'recovery-fx', 77), ('0', 'another-form', 23)]:
        page, case = make_page(form, tag)
        first_row_param = call(exe.address(get_param), page, 0)
        child = call(malloc, 0x100)
        call(exe.address(component_ctor), child, STACK + 4)
        call(exe.address(add_child), page, child)
        calls.clear()
        call(destructors[kind]['address'], page)
        trace = calls[:]
        watched = [page, child, first_row_param]
        disposition = [trace.count(['libc_free', a]) for a in watched]
        assert disposition == [int(kind == '0'), 1, 1]
        if kind == '0':
            assert ['operator_delete', page] in trace
            # The populated constructor allocates intervening chunks in the
            # same allocator classes. The prior empty D0 audit tests reuse.
            assert trace.index(['libc_free', child]) < trace.index(['libc_free', page])
            assert trace.index(['libc_free', first_row_param]) < trace.index(['libc_free', page])
        else:
            assert ['operator_delete', page] not in trace
            call(libc.address('__libc_free'), page)
        cases.append(dict(case, destructor=kind, disposition=disposition,
                          destruction_trace=trace, allocation_identities=watched))
    return dict(original=dict(original, elf_sha256=target['elf'],
                              firmware=target['firmware'], role=target['role']),
                images={str(i.path.relative_to(ROOT)):sha(i.path) for i in images},
                destructor_ranges=destructors, cases=cases, syscalls=syscalls,
                boundaries=dict(base=exe.range(page_base), add=exe.range(add_params),
                                free=libc.range('__libc_free'), delete=cxx.range('_ZdlPv')),
                models=['loader initialization lookup, Linux TLS helper and brk only',
                        'original firmware constructor and allocator code executed'])


if __name__ == '__main__':
    print(json.dumps(observe(), indent=2))
