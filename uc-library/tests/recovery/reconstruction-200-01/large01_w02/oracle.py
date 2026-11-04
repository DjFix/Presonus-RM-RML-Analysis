"""Execute exact ARM app ranges and compiler runtime; no Core firmware execution."""
import hashlib, json, struct, argparse
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC
ROOT = Path(__file__).resolve().parents[5]
PACKETS = ROOT / 'temp/recovery-work/reconstruction-200-01/large-batch01/packets'
ELF = ROOT / 'rootfs/CS18_v13840/home/root/surface'
SHA = '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
OBJ, STACK, STOP = 0x4000000, 0x5000000, 0x6000000

def load():
    assert hashlib.sha256(ELF.read_bytes()).hexdigest() == SHA
    with ELF.open('rb') as f:
        e = ELFFile(f)
        segments = [(s['p_vaddr'], s.data(), s['p_memsz']) for s in e.iter_segments() if s['p_type']=='PT_LOAD']
        symtab = e.get_section_by_name('.symtab')
        symbols = {s.name:s for s in symtab.iter_symbols()}
        records=[]
        for i in range(1,11):
            p=PACKETS / f'large01_w02_{i:02}'
            req=json.loads((p/'request.json').read_text())
            t=req['targets'][0];s=symbols[t['mangled']];sec=e.get_section(s['st_shndx'])
            assert s['st_value']==t['address'] and s['st_size']==t['size']
            offset=sec['sh_offset']+s['st_value']-sec['sh_addr']
            f.seek(offset); b=f.read(s['st_size'])
            text=(p/'ELF_CONTEXT.md').read_text()
            assert hashlib.sha256(b).hexdigest() in text
            records.append(dict(task_id=req['task_id'],elf_sha256=SHA,mangled=t['mangled'],address=t['address'],size=t['size'],section=sec.name,file_offset=offset,sha256=hashlib.sha256(b).hexdigest()))
        for prefix in ['03','04','05']:
            path=next((ROOT/'temp/recovery-work/reconstruction-200-01/expansions01').glob(prefix+'-large01_w02*'))
            expansion=json.loads((path/'expansion.json').read_text())
            native=json.loads((path/'native-context.json').read_text())
            for body in native['bodies'].values():
                sec=e.get_section(body['section_index'])
                offset=sec['sh_offset']+body['address']-sec['sh_addr']
                f.seek(offset);b=f.read(body['size'])
                assert hashlib.sha256(b).hexdigest()==body['bytes_sha256']
                assert offset==body['file_offset']
                records.append(dict(dependency=True,address=body['address'],size=body['size'],section=sec.name,file_offset=offset,sha256=hashlib.sha256(b).hexdigest(),expansion=str((path/'expansion.json').relative_to(ROOT))))
    return segments,records

def execute(segments,rec,task,args):
    u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
    lo=min(x[0] for x in segments)&~4095; hi=(max(x[0]+x[2] for x in segments)+4095)&~4095
    u.mem_map(lo,hi-lo)
    for addr,data,_ in segments:u.mem_write(addr,data)
    u.mem_map(OBJ,0x4000);u.mem_map(STACK,0x10000);u.mem_map(STOP,0x1000)
    u.mem_write(OBJ,b'\xa5'*0x4000)
    u.reg_write(UC_ARM_REG_SP,STACK+0xf000);u.reg_write(UC_ARM_REG_LR,STOP)
    u.reg_write(UC_ARM_REG_R0,OBJ)
    if args:u.reg_write(UC_ARM_REG_R1,args[0]&0xffffffff)
    if len(args)>1:u.reg_write(UC_ARM_REG_R2,args[1]&0xffffffff)
    if task==7:
        # Set each cache to input sentinel: checking all nine isolates wrong index.
        u.mem_write(OBJ+0xb80,struct.pack('<9I',*([args[2]&0xffffffff]*9)))
    connected=not (task==2 and len(args)>2 and args[2]==0)
    u.mem_write(OBJ+0xae0,struct.pack('<I',OBJ+0x3000 if connected else 0))
    u.mem_write(OBJ+0x3000,struct.pack('<I',OBJ+0x3100))
    u.mem_write(OBJ+0x3100,struct.pack('<I',STOP+0x100))
    before=bytes(u.mem_read(OBJ,0x4000)); midi=[];helpers=[]
    def hook(uc,addr,size,_):
        if addr==STOP:uc.emu_stop();return
        if addr==STOP+0x100:
            assert uc.reg_read(UC_ARM_REG_R0)==OBJ+0x3000
            assert uc.reg_read(UC_ARM_REG_R3)==0
            data=bytes(uc.mem_read(uc.reg_read(UC_ARM_REG_R1),uc.reg_read(UC_ARM_REG_R2)))
            midi.append(list(data));uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
        if 0xc0480<=addr<0xc04b0:return
        if 0x1873f0<=addr<0x1873f0+408 or 0x187854<=addr<0x187854+84:
            if addr in (0x1873f0,0x187854):helpers.append(addr)
            return
        if not rec['address']<=addr<rec['address']+rec['size']:raise AssertionError(f'Unexpected execution {addr:x}')
    u.hook_add(UC_HOOK_CODE,hook)
    u.emu_start(rec['address'],STOP,count=3000)
    assert u.reg_read(UC_ARM_REG_PC)==STOP
    after=bytes(u.mem_read(OBJ,0x4000)); changed=[i for i,(a,b) in enumerate(zip(before,after)) if a!=b]
    if task in (1,4,5,8):
        off={1:0xbc4,4:0xae0,5:0xae4,8:0xadd}[task];length=1 if task==8 else 4
        assert all(off<=x<off+length for x in changed)
        out=[int.from_bytes(after[off:off+length],'little')]
    elif task in (3,6):
        assert not changed;out=[u.reg_read(UC_ARM_REG_R0)]
    elif task==2:
        assert not changed and len(midi)==int(connected);out=midi[0] if midi else []
    elif task==7:
        vals=list(struct.unpack('<9I',after[0xb80:0xba4]));out=vals+[len(midi)]+(midi[0] if midi else [])
        assert all(0xb80<=x<0xba4 for x in changed)
    elif task==9:
        assert all(x<4 for x in changed)
        assert int.from_bytes(after[:4],'little')==0x1ea978
        out=[0,after[4:]==before[4:]]
        out=[int(x) for x in out]
    else:
        assert not changed;out=[u.reg_read(UC_ARM_REG_R0)-OBJ]
    return dict(task=task,args=args,output=out,memory_changed=changed,midi=midi,helpers=helpers)

def generate():
    segments,records=load();cases=[]
    tags=[-2147483648,-1,0,0x1fff,0x2000,0x2001,0x2006,0x2007,0x2008,0x9000,2147483647]
    domains={1:[[v] for v in [0,0x123400,0xabcdef]],4:[[v,s] for v in [0,0x123400,0xabcdef] for s in [-1,0,1,99]],5:[[v] for v in [0,0x123400,0xabcdef]],8:[[0],[1]],3:[[t] for t in tags],6:[[t] for t in tags],2:[[t,d] for t in tags for d in [-2147483648,-100,-64,-63,-1,0,1,62,63,64,2147483647]],7:[[t,struct.unpack('<I',struct.pack('<f',v))[0],c] for t in tags for v in [0.,0.0001,0.25,0.5,0.9999,1.] for c in [-1,0,4092,8184,16368,8191,16383]],9:[[]],10:[[]]}
    domains[2] += [[t,d,0] for t in [0x2000,0x2007,0x9000] for d in [-1,0,1]]
    for task in range(1,11):
        for args in domains[task]:cases.append(execute(segments,records[task-1],task,args))
    return dict(version=1,oracle='Unicorn '+unicorn.__version__,range_records=records,cases=cases,limitations='Original app instructions; Actual sendMidiMessage instructions executed; only abstract sink virtual receiver is an explicit external boundary. Actual original compiler float helpers executed. No Core firmware. Pointer values are mapped tokens, original return/static declarations and ARM ABI unresolved. Float domain finite normalized [0,1].')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();d=generate();Path(a.out).write_text(json.dumps(d,indent=2)+'\n');print('Native cases',len(d['cases']))
