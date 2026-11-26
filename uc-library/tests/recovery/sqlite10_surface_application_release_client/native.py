"""Execute release, real original client C1 and real deleting D0 with explicit provider boundaries."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
import elftools
import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UcError
from unicorn.arm_const import (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC)
parser = argparse.ArgumentParser()
parser.add_argument("packet", type=Path)
parser.add_argument("fixture", type=Path)
parser.add_argument("--verify", action="store_true")
args = parser.parse_args()
original = json.loads(args.packet.read_text())["originals"][0]["original"]
ELF = Path(original['elf_path'])
digest = hashlib.sha256(ELF.read_bytes()).hexdigest()
assert digest == original['elf']
NAMES = ('_ZN8Presonus7Surface18SurfaceApplication22releaseClientComponentEPNS_2UC19ClientRootComponentE',
         '_ZN8Presonus2UC19ClientRootComponentC1EPKc', '_ZN8Presonus2UC19ClientRootComponentD0Ev',
         '_ZTVN8Presonus2UC19ClientRootComponentE')
with ELF.open('rb') as s:
    elf = ELFFile(s)
    t = elf.get_section_by_name('.symtab')
    content = {}
    ranges = {}
    assert elf.little_endian and elf["e_machine"] == "EM_ARM"
    for name in NAMES:
        sym, = t.get_symbol_by_name(name)
        sec = elf.get_section(sym['st_shndx'])
        a = sym['st_value']
        p = a-sec['sh_addr']
        size = sym['st_size']
        assert 0 <= p <= sec['sh_size'] - size
        data = sec.data()[p:p + size]
        assert len(data) == size
        content[a] = (name, data)
        ranges[hex(a)] = {
            'name': name, 'size': size, 'section': sym['st_shndx'],
            'section_name': sec.name, 'file_offset': sec['sh_offset'] + p,
            'sha256': hashlib.sha256(data).hexdigest(),
        }
        if name == original['mangled']:
            assert a == original['address'] and size == original['size']
            assert ranges[hex(a)]['file_offset'] == original['file_offset']
            assert sym['st_shndx'] == original['section']
            assert sec.name == original['section_name']
            assert ranges[hex(a)]['sha256'] == original['range_sha256']
            assert data.hex() == original['range_hex']
    boundaries = {
        0x50B9C: ('ClientComponent C2', '_ZN8Presonus2UC15ClientComponentC2EPKc'),
        0x4F680: ('ClientImplementation C2', '_ZN8Presonus2UC20ClientImplementationC2Ev'),
        0x3AE34: ('CStringBuffer<64> C1', '_ZN4Core13CStringBufferILi64EEC1EPKc'),
        0x4EEB8: ('ClientImplementation D2', '_ZN8Presonus2UC20ClientImplementationD2Ev'),
        0x11B5E0: ('CCL Component D2', '_ZN4Core8Portable9ComponentD2Ev'),
    }
    for address, (_, name) in boundaries.items():
        symbol, = t.get_symbol_by_name(name)
        assert symbol['st_value'] == address
    PLT_DELETE = 0xAD5C
    plt = elf.get_section_by_name('.plt')
    assert plt['sh_addr'] <= PLT_DELETE < plt['sh_addr'] + plt['sh_size']
    rel_plt = elf.get_section_by_name('.rel.plt')
    dynsym = elf.get_section(rel_plt['sh_link'])
    # ARM PLT begins with a 20-byte resolver followed by 12-byte entries.
    entry_offset = PLT_DELETE - plt['sh_addr'] - 20
    assert entry_offset >= 0 and entry_offset % 12 == 0
    rel = rel_plt.get_relocation(entry_offset // 12)
    assert dynsym.get_symbol(rel['r_info_sym']).name == '_ZdlPv'
APP, CHILD, INPUT, STACK, STOP = range(0x400000,0x405000,0x1000)
RELEASE, C1, D0, VTABLE = content.keys()
assert (RELEASE,C1,D0,VTABLE) == (0xa6a38,0x51434,0x50cf4,0x1957a0)
HOOKS = {address: name for address, (name, _) in boundaries.items()}
HOOKS[PLT_DELETE] = 'operator delete PLT'

def exercise(nonnull):
    uc=Uc(UC_ARCH_ARM,UC_MODE_ARM)
    for pg in {a & ~4095 for a in (*content,*HOOKS,APP,CHILD,INPUT,STACK,STOP)}:
        uc.mem_map(pg,4096)
    for a,(_, data) in content.items():
        uc.mem_write(a,data)
    app_seed = bytes([0xA5]) * 4096
    uc.mem_write(APP, app_seed)
    uc.mem_write(INPUT,b'fixture client\0')
    events=[]
    def trace(m,a,n,user):
        r0=m.reg_read(UC_ARM_REG_R0)
        if a in (C1,D0):
            assert r0==CHILD
            events.append((content[a][0],r0))
        if a not in HOOKS:
            assert any(start <= a < start+len(data) for start,(_,data) in content.items()), hex(a)
            return
        events.append((HOOKS[a],r0))
        if a == PLT_DELETE:
            assert r0==CHILD
            m.mem_unmap(CHILD,4096)
        m.reg_write(UC_ARM_REG_PC,m.reg_read(UC_ARM_REG_LR))
    uc.hook_add(UC_HOOK_CODE,trace)
    def run(entry,r0,r1):
        for reg,value in ((UC_ARM_REG_R0,r0),(UC_ARM_REG_R1,r1),(UC_ARM_REG_SP,STACK+2048),(UC_ARM_REG_LR,STOP)):
            uc.reg_write(reg,value)
        uc.emu_start(entry,STOP,count=1024)
        assert uc.reg_read(UC_ARM_REG_PC)==STOP
    if nonnull:
        run(C1,CHILD,INPUT)
        vptr,=struct.unpack('<I',uc.mem_read(CHILD,4))
        target,=struct.unpack('<I',uc.mem_read(vptr+8,4))
        assert (vptr,target) == (VTABLE+8,D0)
    run(RELEASE,APP,CHILD if nonnull else 0)
    if nonnull:
        assert events[-4:] == [(content[D0][0],CHILD), ('ClientImplementation D2',CHILD+0x88),
                               ('CCL Component D2',CHILD), ('operator delete PLT',CHILD)]
        try:
            uc.mem_read(CHILD,1)
        except UcError:
            pass
        else:
            raise AssertionError('guest allocation survived deleting boundary')
    else:
        assert not events
    assert bytes(uc.mem_read(APP, 4096)) == app_seed
    return {'nonnull': nonnull, 'events': [list(event) for event in events],
            'surface_unchanged': True, 'allocation_unmapped': nonnull}
result = {
    'elf':str(ELF),'elf_sha256':digest,
    'inputs': ranges,
    'versions': {'unicorn': unicorn.__version__, 'pyelftools': elftools.__version__},
    'scope':'Actual original release, ClientRootComponent C1, vtable bytes and D0. Named subordinate constructors and destructors are explicit hooks. The called delete PLT boundary unmaps the matching guest allocation; actual firmware allocator implementation is outside the fixture.',
    'cases':[exercise(False),exercise(True)],
}
if args.verify:
    assert result == json.loads(args.fixture.read_text())
else:
    args.fixture.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
print(f"Native executions: {len(result['cases'])}")
