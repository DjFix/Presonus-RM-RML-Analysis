"""Execute sealed ARM target prefixes; halt before unresolved direct callees.

This is bounded original-instruction evidence, not full lifecycle validation.
No Core implementation instructions execute. No expected values use C++.
"""
from pathlib import Path
import hashlib
import json
import struct
import sys
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP, UC_ARM_REG_LR

PACKETS = Path('temp/recovery-work/ranked20-cycle01/batch02/packets')
OBJ, OTHER, STACK, STOP = 0x1000000, 0x1001000, 0x1100000, 0x1200000

def run(packet, variant):
    c = json.loads((packet / 'context.json').read_text())
    nc = c['native_context']
    nid = c['native_roots'][0]
    m = nc['nodes'][nid]['metadata']
    body = nc['bodies'][nid]
    elfpath = Path(nc['binaries'][m['elf']]['path'])
    raw = elfpath.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == m['elf']
    block = raw[body['file_offset']:body['file_offset'] + body['size']]
    assert hashlib.sha256(block).hexdigest() == body['bytes_sha256']
    u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    with elfpath.open('rb') as f:
        elf = ELFFile(f)
        # Map load segments one page at a time to handle overlap.
        pages = set()
        for s in elf.iter_segments():
            if s['p_type'] != 'PT_LOAD':
                continue
            start, length = int(s['p_vaddr']), int(s['p_memsz'])
            for page in range(start & ~4095, (start + length + 4095) & ~4095, 4096):
                if page not in pages:
                    u.mem_map(page, 4096)
                    pages.add(page)
            u.mem_write(start, s.data())
    u.mem_map(OBJ, 0x3000)
    u.mem_map(STACK, 0x10000)
    u.mem_map(STOP, 4096)
    u.mem_write(OBJ, bytes([0xa5]) * 256)
    u.mem_write(OTHER, bytes([0]) * 256)
    u.mem_write(OTHER + 0x34, struct.pack('<I', 9))
    # Focus null / same-pointer / independent-pointer prefix observations.
    if packet.name.endswith('_09'):
        a, b = [(0, 0), (OTHER, 0), (0, OTHER), (OTHER, OTHER)][variant]
        u.mem_write(OBJ + 0x58, struct.pack('<II', a, b))
    u.reg_write(UC_ARM_REG_R0, OBJ)
    u.reg_write(UC_ARM_REG_R1, 0x12345678)
    u.reg_write(UC_ARM_REG_R2, 0x87654321)
    u.reg_write(UC_ARM_REG_SP, STACK + 0xf000)
    u.reg_write(UC_ARM_REG_LR, STOP)
    calls = {e['metadata']['target_address']: nc['nodes'][e['dst']]['label'] for e in nc['edges'] if e['src'] == nid and e['kind'] == 'ELF_CALLS'}
    writes, trace, boundary = [], [], []
    def code(uc, addr, size, _):
        trace.append(addr)
        if addr in calls:
            boundary.append({'address':addr, 'identity':calls[addr], 'arguments':[uc.reg_read(r) for r in [UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3]]})
            uc.emu_stop()
    def write(uc, access, addr, size, value, _):
        if OBJ <= addr < OBJ + 0x3000:
            writes.append({'address':addr, 'size':size, 'value':value})
    u.hook_add(UC_HOOK_CODE, code)
    u.hook_add(UC_HOOK_MEM_WRITE, write)
    u.emu_start(body['address'], STOP, count=1000)
    assert len(boundary) == 1, packet
    return {'task_id':c['task_id'],'mangled':m['mangled'],'elf_sha256':m['elf'],'section':body['section'],'file_offset':body['file_offset'],'size':body['size'],'range_sha256':body['bytes_sha256'],'variant':variant,'executed_addresses':trace[:-1],'boundary':boundary[0],'writes':writes,'object_hex':bytes(u.mem_read(OBJ,256)).hex(),'referenced_counter':struct.unpack('<I',u.mem_read(OTHER+0x34,4))[0]}

def main():
    cases = []
    for p in sorted(PACKETS.glob('rank20c01_w02_*')):
        for variant in range(4 if p.name.endswith('_09') else 1):
            cases.append(run(p, variant))
    result = {'kind':'original ARM execution; unresolved call boundary halt','limitations':'No callee replaced or executed; prefix memory/call observations only; does not validate completion, return, cleanup or portable behavior.','cases':cases}
    result['meter'] = meter_observations()
    if len(sys.argv)>2:
        fixture=json.loads(Path(sys.argv[2]).read_text())
        assert result['meter']==fixture['meter']
        assert {k:v for k,v in result.items() if k!='meter'}==fixture['native_prefix']
    Path(sys.argv[1]).write_text(json.dumps(result,indent=2)+'\n')
    print(f'{len(cases)} original target-prefix executions; all stopped at actual direct call boundary')


def meter_observations():
    """Original isHorizontal + expanded isVertical, real getSize boundary.

    The pinned source provider's getSize contract is adapted as an immutable
    supplied four-int rectangle pointer. No original Core instructions execute.
    """
    import random
    p = PACKETS / 'rank20c01_w02_11'
    c = json.loads((p/'context.json').read_text())
    exp_path = Path('temp/recovery-work/ranked20-cycle01/expansions/w02_11_0/expansion.json')
    exp = json.loads(exp_path.read_text())
    assert exp['parent_manifest_sha256'] == hashlib.sha256((p/'context.json').read_bytes()).hexdigest()
    raw = Path('rootfs/CS18_v13840/home/root/surface').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
    b = exp['body']
    assert hashlib.sha256(raw[b['file_offset']:b['file_offset']+b['size']]).hexdigest() == b['bytes_sha256']
    # Only the two application bodies and synthetic provider-boundary page map.
    u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    u.mem_map(0x64000, 0x2000)
    for body in [b, next(iter(c['native_context']['bodies'].values()))]:
        u.mem_write(body['address'],raw[body['file_offset']:body['file_offset']+body['size']])
    u.mem_map(0x10e000,4096)
    u.mem_map(OBJ,0x3000)
    u.mem_map(STACK,0x10000)
    u.mem_map(STOP,4096)
    calls=[]
    # Use named PC constant: numeric register ids are not ARM register numbers.
    from unicorn.arm_const import UC_ARM_REG_PC
    def boundary(uc,addr,size,_):
        if addr == 0x10e9a8:
            calls.append({'address':addr,'this':uc.reg_read(UC_ARM_REG_R0)})
            uc.reg_write(UC_ARM_REG_R0,OTHER)
            uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
    u.hook_add(UC_HOOK_CODE,boundary)
    rects=[[0,0,0,0],[0,0,10,10],[0,0,10,11],[0,0,11,10],[-50,-40,-20,-10],[8,9,-12,-11],[0,0,-10,10],[0,0,10,-10]]
    rng=random.Random(20261103)
    rects += [[rng.randint(-100000,100000) for _ in range(4)] for _ in range(128)]
    observations=[]
    for rect in rects:
        calls.clear()
        u.mem_write(OBJ,bytes([0xa5])*256)
        u.mem_write(OTHER,struct.pack('<4i',*rect))
        u.reg_write(UC_ARM_REG_R0,OBJ)
        u.reg_write(UC_ARM_REG_SP,STACK+0xf000)
        u.reg_write(UC_ARM_REG_LR,STOP)
        u.emu_start(0x64f10,STOP,count=200)
        assert len(calls)==1
        assert bytes(u.mem_read(OBJ,256))==bytes([0xa5])*256
        assert bytes(u.mem_read(OTHER,16))==struct.pack('<4i',*rect)
        observations.append({'rect':rect,'return_word':u.reg_read(UC_ARM_REG_R0),'provider_calls':list(calls),'object_and_rectangle_unchanged':True})
    return {'expansion_path':str(exp_path),'expansion_sha256':hashlib.sha256(exp_path.read_bytes()).hexdigest(),'isVertical_range':{k:b[k] for k in ['address','size','section','file_offset','bytes_sha256']},'domain':'136 rectangles; zero/square/tall/wide/negative origins/inverted extents plus seeded rectangles; differences within int32; getSize boundary supplies immutable four-int rect.','cases':observations}

if __name__ == '__main__': main()
