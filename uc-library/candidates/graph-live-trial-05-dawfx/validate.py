import sys,json,hashlib,subprocess,pathlib,time,datetime,struct,itertools,os
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
BASE=pathlib.Path('uc-library/candidates/graph-live-trial-05-dawfx'); WORK=pathlib.Path('temp/recovery-work/graph-live-trial-05/dawfx-worker'); WORK.mkdir(parents=True,exist_ok=True)
SOURCE='uc-library/src/Presonus/Surface/DawFxPageComponent.cpp'; HEADER='uc-library/include/presonus/surface/DawFxPageComponent.hpp'; TEST='uc-library/tests/graph_trial05_dawfx_tests.cpp'; EXE=str(WORK/'replay')
PACKETS=[pathlib.Path(f'temp/recovery-work/graph-live-trial-05/trial05_dawfx_{i}-packet') for i in range(1,6)]
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def run(args):
 t=time.monotonic(); started=datetime.datetime.now(datetime.timezone.utc).isoformat(); r=subprocess.run(args,capture_output=True,text=True); entry=dict(argv=args,start=started,duration_seconds=time.monotonic()-t,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)
 with (WORK/'commands.jsonl').open('a') as f:f.write(json.dumps(entry)+'\n')
 if r.returncode:raise RuntimeError(entry)
 return r.stdout

def compile():
 inc='temp/core-upstream/root-integration-01/upstream-core/sdk/include/presonus-core-5'
 args=['/usr/bin/c++','-std=c++20','-fno-rtti','-Ulinux','-pthread','-Iuc-library/include','-I'+inc,SOURCE,TEST,'temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a','-lpthread','-ldl','-o',EXE]
 run(args)
def symbols():
 out=run(['nm','--defined-only',EXE]);
 for p in PACKETS:
  name=json.load(open(p/'context.json'))['originals'][0]['original']['mangled'];assert name in out,name
 (BASE/'symbols.txt').write_text(out)
def oracle():
 elfpath=pathlib.Path('rootfs/CS18_v13840/home/root/surface');assert sha(elfpath)=='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
 elf=ELFFile(elfpath.open('rb')); segments=[(s['p_vaddr'],s.data()) for s in elf.iter_segments() if s['p_type']=='PT_LOAD']
 ranges=[]
 for p in PACKETS:
  c=json.load(open(p/'context.json')); o=c['originals'][0]['original'];section=elf.get_section(int(o['section_json'])); offset=section['sh_offset']+o['address']-section['sh_addr'];data=elfpath.read_bytes()[offset:offset+o['size']]; body=next(iter(c['native_context']['bodies'].values())); assert hashlib.sha256(data).hexdigest()==body['bytes_sha256'] if 'bytes_sha256' in body else True
  ranges.append(dict(original=o,file_offset=offset,sha256=hashlib.sha256(data).hexdigest()))
 cases=[]
 for op in range(1,6):
  for present,value,folder,count,a,z,arg in itertools.product([0,1],[-2.,0.,0.99,1.,1.5,1.99,2.], [0,1],[0,1,5,6,10,11,31],[-1,0,5],[0,10],[-7,0,4,5,99] if op<3 else [0]):
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x400000)
   for addr,data in segments:u.mem_write(addr,data)
   obj=0x200000;param=0x210000;vtable=0x211000;valuefn=0x212000;stack=0x300000;stop=0x320000
   def put(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
   def get(a):return struct.unpack('<i',u.mem_read(a,4))[0]
   put(obj+192,param if present else 0);put(obj+196,a);put(obj+200,z);put(param,vtable);put(vtable+68,valuefn)
   trace=[]
   def hook(u,pc,size,user):
    ret=None
    if pc==valuefn: trace.append('value');ret=struct.unpack('<I',struct.pack('<f',value))[0]
    elif pc==0x1877f8:ret=int(struct.unpack('<f',struct.pack('<I',u.reg_read(UC_ARM_REG_R0)))[0])
    elif pc==0xb74f0:trace.append('folder');ret=0x220000 if folder else 0
    elif pc==0x52e20:trace.append('count');ret=count
    elif pc==0xb7590:trace.append('update'+str(u.reg_read(UC_ARM_REG_R1)));ret=0
    elif pc==stop:u.emu_stop();return
    if ret is not None:u.reg_write(UC_ARM_REG_R0,ret&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
   u.hook_add(UC_HOOK_CODE,hook);u.reg_write(UC_ARM_REG_SP,stack);u.reg_write(UC_ARM_REG_LR,stop);u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_R1,arg&0xffffffff)
   u.emu_start(ranges[op-1]['original']['address'],stop+4,count=500)
   result=u.reg_read(UC_ARM_REG_R0)
   if op<3:result=0
   elif op==4:result-=obj
   elif result>=2**31:result-=2**32
   inputs=[op,present,value,folder,count,a,z,arg]; output=[str(result),str(get(obj+196)),str(get(obj+200))]+trace
   cases.append(dict(inputs=inputs,output=output))
 (BASE/'fixtures.json').write_text(json.dumps(dict(ranges=ranges,cases=cases,stubs=['getFolder','getUsedCount','updateList','Parameter::getValue','__aeabi_f2iz finite representable float conversion']),indent=2))
 print('original executions',len(cases))
def replay(exe,fixture):
 f=json.load(open(fixture))
 for c in f['cases']:
  actual=subprocess.check_output([exe]+list(map(str,c['inputs'])),text=True).split();assert actual==c['output'],(c,actual)
 print('differential cases',len(f['cases']))
if __name__=='__main__':
 mode=sys.argv[1]
 if mode=='compile':compile()
 elif mode=='symbols':symbols()
 elif mode=='oracle':oracle()
 elif mode=='replay':replay(sys.argv[2] if len(sys.argv)>2 else EXE,sys.argv[3] if len(sys.argv)>3 else str(BASE/'fixtures.json'))
