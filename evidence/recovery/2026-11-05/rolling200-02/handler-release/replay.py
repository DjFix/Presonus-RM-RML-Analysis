#!/usr/bin/env python3
"""Exact app-body ARM oracle and actual provider C++ replay; no ARM Core execution."""
import argparse, hashlib, json, pathlib, subprocess, sys
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_SP
ROOT = pathlib.Path.cwd()
OUT = ROOT / 'temp/recovery-work/rolling200-02/handler-release-local'
EVID = ROOT / 'evidence/recovery/2026-11-05/rolling200-02/handler-release'
ELF = ROOT / 'rootfs/RML16AI_Rack_13731/home/root/mixer'
NAME = '_ZN8Presonus4NOAA12TCardHandler7releaseEv'
START, SIZE, OFFSET = 0x9f808,136,0x97808
EXPECTED_ELF='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def oracle():
    assert digest(ELF)==EXPECTED_ELF
    raw=ELF.read_bytes()
    assert hashlib.sha256(raw[OFFSET:OFFSET+SIZE]).hexdigest()=='62aaf35ab478be70f9798e2c1cf3edbb092be081d15e942ac6aff29ea6bdbcf5'
    with ELF.open('rb') as f:
        elf=ELFFile(f)
        matches=[s for sec in elf.iter_sections() if sec['sh_type']=='SHT_SYMTAB' for s in sec.iter_symbols() if s.name==NAME]
        assert len(matches)==1
        sym=matches[0]; sec=elf.get_section(sym['st_shndx'])
        assert (sym['st_value'],sym['st_size'],sym['st_shndx'])==(START,SIZE,12)
        assert sec['sh_offset']+START-sec['sh_addr']==OFFSET
        segments=[(s['p_vaddr'],s['p_memsz'],s.data()) for s in elf.iter_segments() if s['p_type']=='PT_LOAD']
    records=[]
    for present in [False,True]:
      for initial in [0,0x7f]:
        u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
        pages=set()
        for addr,size,data in segments:
            for page in range(addr&~4095,(addr+size+4095)&~4095,4096):
                if page not in pages:u.mem_map(page,4096);pages.add(page)
            u.mem_write(addr,data)
        this,spi,stack=0x60000000,0x60001000,0x70000000
        u.mem_map(this,0x3000);u.mem_map(stack,0x10000)
        singleton=int.from_bytes(raw[OFFSET+128:OFFSET+132],'little')
        assert singleton==4805480
        u.mem_write(singleton,(spi if present else 0).to_bytes(4,'little'))
        u.mem_write(this+100,bytes([initial]));u.reg_write(UC_ARM_REG_R0,this);u.reg_write(UC_ARM_REG_SP,stack+0x8000)
        events=[];providers=[];writes=[];done=[]
        def write(uc,access,addr,size,value,data):
            pc=uc.reg_read(UC_ARM_REG_PC)
            assert (stack<=addr and addr+size<=stack+0x10000) or (pc==0x9f83c and addr==this+100 and size==1) or (pc==0x9f864 and spi<=addr and addr+size<=spi+8) or (pc==0x9f868 and addr==singleton and size==4),(hex(pc),hex(addr),size)
            if addr==this+100:
                assert value==1;events.append('stop=1;')
            if not stack<=addr<stack+0x10000:writes.append({'pc':pc,'address':addr,'size':size,'value':value})
        def code(uc,pc,size,data):
            if START<=pc<START+128:return
            r0=uc.reg_read(UC_ARM_REG_R0)
            if pc==0xa7e4:
                assert not present and r0==456;providers.append('operator new(456)');uc.reg_write(UC_ARM_REG_R0,spi)
            elif pc==0xa2e64:
                assert r0==spi;providers.append('TCardSPI constructor boundary')
            elif pc==0x126cfc:
                assert r0==spi;providers.append('CCL Deletable::addInstance boundary')
            elif pc==0xa2c00:
                assert r0==spi;providers.append('actual SPI release provider boundary');events.append('spi.release;')
            elif pc==0x10e800:
                assert r0==this+4 and uc.mem_read(this+100,1)==b'\x01'
                events.append('terminate;');providers.append('CCL legacy terminate boundary');done.append(True);uc.emu_stop();return
            else:raise AssertionError('unexpected PC '+hex(pc))
            uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_MEM_WRITE,write);u.hook_add(UC_HOOK_CODE,code)
        u.emu_start(START,0,count=200)
        assert done and ''.join(events)=='spi.release;stop=1;terminate;'
        records.append({'present':present,'initial_native_stop_byte':initial,'events':events,'provider_boundaries':providers,'private_writes':writes})
    return {'original':{'elf_sha256':EXPECTED_ELF,'mangled':NAME,'address':START,'size':SIZE,'section':12,'file_offset':OFFSET,'range_sha256':hashlib.sha256(raw[OFFSET:OFFSET+SIZE]).hexdigest()},'cases':records,'native_core_executed':False,'provider_boundary_model':'Constructor/allocation/registration and release/terminate hooks only; app instructions execute under guarded PC/private-write whitelist; no syscalls'}
def command(argv):
    print(json.dumps(argv),flush=True)
    subprocess.run(argv,check=True,timeout=120)
def compile_():
    OUT.mkdir(parents=True,exist_ok=True)
    sdk='temp/core-upstream/root-integration-01/upstream-core/sdk'
    command(['g++','-std=c++17','-O0','-g','-pthread','-Iuc-library/include','-I'+sdk+'/include/presonus-core-5','uc-library/src/Presonus/NOAA/TCardHandlerRelease.cpp','uc-library/tests/recovery/TCardHandlerReleaseReplay.cpp','-Wl,--wrap=_ZN8Presonus4NOAA8TCardSPI7releaseEv','-Wl,--wrap=_ZN4Core8Platform11PosixThread9terminateEv','-Wl,--start-group','temp/core-upstream/root-integration-01/libpresonus_uc.a',sdk+'/lib/libcorelib.a',sdk+'/lib/libpresonus_core_allocator.a','temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a','-Wl,--end-group','-ldl','-o',str(OUT/'replay')])
def symbols():
    result=subprocess.run(['nm','--defined-only',str(OUT/'replay')],text=True,capture_output=True,check=True)
    exact=[line for line in result.stdout.splitlines() if line.split()[-1:]==[NAME]]
    assert len(exact)==1,exact
    print(exact[0])
def replay(binary=None):
    proof=oracle()
    fixture=EVID/'fixture.txt'
    expected=''.join(proof['cases'][0]['events'])+'\n'
    assert fixture.read_text()==expected
    for mode in ['absent','present']:
        for seed in [0,1,255]:command([str(binary or OUT/'replay'),mode,str(seed),str(fixture)])
    print('PASS 4 exact ARM app executions; 6 actual SPI/CCL started-thread source-provider cases')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['oracle','compile','symbols','replay']);p.add_argument('--binary');a=p.parse_args()
    if a.action=='oracle':
        result=oracle();(EVID/'native.json').write_text(json.dumps(result,indent=2)+'\n');(EVID/'fixture.txt').write_text(''.join(result['cases'][0]['events'])+'\n')
    elif a.action=='compile':compile_()
    elif a.action=='symbols':symbols()
    else:replay(a.binary)
