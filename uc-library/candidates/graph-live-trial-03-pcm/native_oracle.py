"""Execute only hash-bound original ARM instructions; never import the port."""
import hashlib, json, pathlib, random, struct
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_MEM_WRITE, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC

OUT = pathlib.Path('uc-library/candidates/graph-live-trial-03-pcm')
ELF = pathlib.Path('rootfs/CS18_v13840/home/root/surface')
sha = lambda data: hashlib.sha256(data).hexdigest()
raw = ELF.read_bytes()
assert sha(raw) == '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
with ELF.open('rb') as handle:
    section = ELFFile(handle).get_section(12)
    assert section.name == '.text'
    offset = section['sh_offset'] + 0xdb368 - section['sh_addr']
assert offset == 0xd3368
body = raw[offset:offset+20]
assert sha(body) == '19652dbd053a820971ca11a6751c58dbb46c4cc0e1cce375e71a683cbb64bc91'
rng = random.Random(4104)
values = list(range(-1024, 1025)) + [-2147483648, -2147483647, 2147483646, 2147483647] + [rng.randint(-2147483648, 2147483647) for _ in range(4096)]
rows, traces = [], []
for i, value in enumerate(values):
    machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    machine.mem_map(0xdb000, 4096)
    machine.mem_write(0xdb368, body)
    machine.mem_map(0x200000, 8192)
    machine.mem_map(0x300000, 4096)
    machine.mem_map(0x400000, 4096)
    machine.reg_write(UC_ARM_REG_R0, 0x300000)
    machine.reg_write(UC_ARM_REG_R1, value & 0xffffffff)
    machine.reg_write(UC_ARM_REG_SP, 0x201000)
    machine.reg_write(UC_ARM_REG_LR, 0x400000)
    writes, pcs = [], []
    machine.hook_add(UC_HOOK_MEM_WRITE, lambda uc, access, address, size, data, user: writes.append([address,size,data]))
    machine.hook_add(UC_HOOK_CODE, lambda uc, address, size, user: pcs.append(address))
    machine.emu_start(0xdb368, 0x400000, count=16)
    assert machine.reg_read(UC_ARM_REG_PC) == 0x400000
    assert machine.reg_read(UC_ARM_REG_SP) == 0x201000
    assert pcs == list(range(0xdb368, 0xdb37c, 4))
    assert len(writes) == 4 and all(0x200ff0 <= w[0] < 0x201000 for w in writes)
    assert machine.mem_read(0x300000,4096) == bytes(4096)
    result = machine.reg_read(UC_ARM_REG_R0)
    rows.append(f'{value} {result}\n')
    if i < 2 or value in (-2147483648,2147483647):
        traces.append(dict(input=value, output=result, pcs=pcs, writes=writes))
(OUT/'fixtures.txt').write_text(''.join(rows))
(OUT/'native-proof.json').write_text(json.dumps(dict(elf=str(ELF), elf_sha256=sha(raw), section='.text', section_index=12,address=0xdb368,offset=offset,size=20,range_sha256=sha(body),unicorn=unicorn.__version__,producer_sha256=sha(pathlib.Path(__file__).read_bytes()),cases=len(rows),memory='mapped zeroed borrowed this region, initialized stack, LR sentinel; no external calls; all executions assert only four stack writes, unchanged this memory, restored SP and exact instruction trace',traces=traces),indent=2)+'\n')
print(f'{len(rows)} original ARM executions; ELF/range hashes and stack/object writes checked')
