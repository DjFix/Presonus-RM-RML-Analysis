"""Independent execution of hash-bound original EQControl ARM ranges."""
import hashlib,json,pathlib,struct
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
from elftools.elf.elffile import ELFFile
ROOT=pathlib.Path(__file__).resolve().parents[5]
ELF=ROOT/'rootfs/CS18_v13840/home/root/surface'
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
OBJ=0x400000; BANDS=0x410000; STACK=0x500000; STOP=0x600000

def execute(index,count,states,target):
    raw=ELF.read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
    packet=ROOT/f'temp/recovery-work/graph-live-trial-08/batch03/packets/trial08_eq_{target}'
    j=json.loads((packet/'native-context.json').read_text());body=j['bodies'][j['roots'][0]]
    with ELF.open('rb') as f:
        elf=ELFFile(f); sec=elf.get_section(body['section_index'])
        offset=sec['sh_offset']+body['address']-sec['sh_addr']
        assert offset==body['file_offset']
    code=raw[offset:offset+body['size']];assert hashlib.sha256(code).hexdigest()==body['bytes_sha256']
    u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
    u.mem_map(0x10000,0x280000);u.mem_write(body['address'],code)
    u.mem_map(OBJ,0x20000);u.mem_map(STACK,0x10000);u.mem_map(STOP,0x1000)
    u.mem_write(OBJ+0x70,struct.pack('<I',count));u.mem_write(OBJ+0xf0,struct.pack('<I',BANDS))
    initial=bytearray(40*max(count,1))
    for i,(on,enabled,dirty) in enumerate(states):initial[40*i+8]=on;initial[40*i+9]=enabled;initial[40*i+20]=dirty
    u.mem_write(BANDS,bytes(initial));u.reg_write(UC_ARM_REG_R0,OBJ);u.reg_write(UC_ARM_REG_R1,index&0xffffffff)
    u.reg_write(UC_ARM_REG_SP,STACK+0x8000);u.reg_write(UC_ARM_REG_LR,STOP)
    u.emu_start(body['address'],STOP,count=1000)
    assert u.reg_read(UC_ARM_REG_PC)==STOP
    final=bytes(u.mem_read(BANDS,len(initial)))
    return {'target':target,'index':index,'count':count,'states':states,'result':u.reg_read(UC_ARM_REG_R0) if target==5 else None,'dirty':[final[40*i+20] for i in range(count)],'writes':[[i,a,b] for i,(a,b) in enumerate(zip(initial,final)) if a!=b],'range':{k:body[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']},'calls':[]}

def main():
    cases=[]
    for count in [0,1,3]:
        for index in [-1,0,1,2,3,2147483647]:
            for pattern in [0,1,2,3]:
                states=[[int((i+pattern)%2),int((i+pattern)//2%2),7] for i in range(count)]
                for t in [2,5]:cases.append(execute(index,count,states,t))
    return cases

# Virtual dispatch is an explicitly modeled boundary. The original target body
# performs every selection/null check; no Core body is reconstructed or executed.
def getter_cases():
    raw=ELF.read_bytes(); cases=[]
    for target,slot in [(8,12),(9,4),(10,8)]:
      packet=ROOT/f'temp/recovery-work/graph-live-trial-08/batch03/packets/trial08_eq_{target}'
      j=json.loads((packet/'native-context.json').read_text());body=j['bodies'][j['roots'][0]]
      for count in [0,1,3]:
       for index in [-1,0,1,2,3]:
        for present in [False,True]:
         u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x10000,0x280000)
         # Original complete range includes the trailing literal pool.
         u.mem_write(body['address'],raw[body['file_offset']:body['file_offset']+body['size']])
         u.mem_map(OBJ,0x20000);u.mem_map(STACK,0x10000);u.mem_map(STOP,0x2000)
         def w(a,v):u.mem_write(a,struct.pack('<I',v))
         w(OBJ+0x78,BANDS);w(OBJ+0x7c,count)
         param=OBJ+0x1000;vtable=OBJ+0x2000;hook=STOP+0x1000;value=0x41340000
         for band in range(count):w(BANDS+24*band+slot,param if present else 0)
         w(param,vtable);w(vtable+0x44,hook)
         calls=[]
         def cb(uc,addr,size,user):
          if addr==hook:
           calls.append({'kind':'parameter-virtual-0x44','object':uc.reg_read(UC_ARM_REG_R0)-OBJ,'return_bits':value})
           uc.reg_write(UC_ARM_REG_R0,value);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
         u.hook_add(UC_HOOK_CODE,cb)
         u.reg_write(UC_ARM_REG_R0,OBJ);u.reg_write(UC_ARM_REG_R1,index&0xffffffff);u.reg_write(UC_ARM_REG_SP,STACK+0x8000);u.reg_write(UC_ARM_REG_LR,STOP)
         u.emu_start(body['address'],STOP,count=1000);assert u.reg_read(UC_ARM_REG_PC)==STOP
         cases.append({'target':target,'index':index,'count':count,'present':present,'parameter_return_bits':value,'result_bits':u.reg_read(UC_ARM_REG_R0),'calls':calls,'sentinel':'zero-initialized NOBITS BandParams error; no nonnull sentinel claim'})
    return cases

def buffered_cases():
 raw=ELF.read_bytes();p=ROOT/'temp/recovery-work/graph-live-trial-08/batch03/packets/trial08_eq_4';j=json.loads((p/'native-context.json').read_text());b=j['bodies'][j['roots'][0]];cases=[]
 for state in [0,1]:
  for present in [0,1]:
   for valid in [0,1]:
    u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x10000,0x280000);u.mem_write(b['address'],raw[b['file_offset']:b['file_offset']+b['size']]);u.mem_map(OBJ,0x20000);u.mem_map(STACK,0x10000);u.mem_map(STOP,0x2000)
    param=OBJ+0x1000;vtable=OBJ+0x2000;hook=STOP+0x1000
    def w(a,v):u.mem_write(a,struct.pack('<I',v))
    w(OBJ+0x114,param if present else 0);u.mem_write(OBJ+0x118,bytes([valid,1-state]));w(param,vtable);w(vtable+4,hook);calls=[]
    def cb(uc,addr,size,user):
     if addr==hook:
      calls.append('release');uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
     elif addr==0x6dbe0:
      calls.append('initBands');uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
    u.hook_add(UC_HOOK_CODE,cb);u.reg_write(UC_ARM_REG_R0,OBJ);u.reg_write(UC_ARM_REG_R1,state);u.reg_write(UC_ARM_REG_SP,STACK+0x8000);u.reg_write(UC_ARM_REG_LR,STOP);u.emu_start(b['address'],STOP,count=1000);assert u.reg_read(UC_ARM_REG_PC)==STOP
    cases.append({'target':4,'state':state,'present':present,'valid':valid,'buffered':u.mem_read(OBJ+0x119,1)[0],'final_present':int(struct.unpack('<I',u.mem_read(OBJ+0x114,4))[0]!=0),'final_valid':u.mem_read(OBJ+0x118,1)[0],'calls':calls,'boundary':'release and initBands are modeled app boundaries; no full initBands/render claim'})
 return cases

def provider_composition_cases():
 raw=ELF.read_bytes();cases=[]
 def fb(v):return struct.unpack('<I',struct.pack('<f',v))[0]
 def bf(v):return struct.unpack('<f',struct.pack('<I',v))[0]
 for target in [1,3,6]:
  j=json.loads((ROOT/f'temp/recovery-work/graph-live-trial-08/batch03/packets/trial08_eq_{target}/native-context.json').read_text());b=j['bodies'][j['roots'][0]]
  values=([20.,200.,1000.,10000.,20000.] if target==1 else ([-12.,-6.,0.,6.,12.] if target==3 else [0,1,3,5]))
  for value in values:
   for cap_extra in ([0,2] if target==6 else [0]):
    u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x10000,0x280000);u.mem_write(b['address'],raw[b['file_offset']:b['file_offset']+b['size']]);u.mem_map(OBJ,0x20000);u.mem_map(STACK,0x10000);u.mem_map(STOP,0x1000)
    calls=[]
    def w(a,v):u.mem_write(a,struct.pack('<I',v))
    if target==6:w(OBJ+0x104,BANDS);w(OBJ+0x108,int(value));w(OBJ+0x10c,int(value)+cap_extra)
    def cb(uc,a,size,user):
     r0=uc.reg_read(UC_ARM_REG_R0);r1=uc.reg_read(UC_ARM_REG_R1)
     if a in [0xe8a70,0xe8238,0xe81b0]:
      calls.append({'provider':hex(a),'argument_bits':r1})
      # Selected actual source-provider semantics, finite asymmetric ranges.
      # Frequency normalizer intentionally uses a supplied linear adapter;
      # original unavailable LogInterpolator behavior is not claimed.
      def f32(x):return bf(fb(x))
      arg=bf(r1)
      if a==0xe8a70: v=f32(f32(max(20.,min(20000.,arg))-20.)/19980.)
      elif a==0xe8238:v=f32(f32(max(-12.,min(12.,arg))+12.)/24.)
      else:
       lo,hi=(10.,110.) if target==1 else (20.,220.)
       v=f32(f32(max(0.,min(1.,arg))*f32(hi-lo))+lo)
      uc.reg_write(UC_ARM_REG_R0,fb(v))
     elif a==0x18714c:uc.reg_write(UC_ARM_REG_R0,fb(bf(r0)-bf(r1)))
     elif a==0x187150:uc.reg_write(UC_ARM_REG_R0,fb(bf(r0)+bf(r1)))
     elif a==0x1877f8:uc.reg_write(UC_ARM_REG_R0,int(bf(r0)))
     elif a==0x6f434:
      calls.append({'provider':'Core vector resize','requested':r1});w(OBJ+0x10c,r1);uc.reg_write(UC_ARM_REG_R0,1)
     else:return
     uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
    u.hook_add(UC_HOOK_CODE,cb);u.reg_write(UC_ARM_REG_R0,OBJ);u.reg_write(UC_ARM_REG_R1,(OBJ+0x3000) if target==6 else fb(value));u.reg_write(UC_ARM_REG_SP,STACK+0x8000);u.reg_write(UC_ARM_REG_LR,STOP);u.emu_start(b['address'],STOP,count=1000);assert u.reg_read(UC_ARM_REG_PC)==STOP
    if target==6:
     out=struct.unpack('<I',u.mem_read(OBJ+0x108,4))[0];stored=struct.unpack('<I',u.mem_read(BANDS+int(value)*4,4))[0];result=[out,int(stored==OBJ+0x3000)]
    else:result=[u.reg_read(UC_ARM_REG_R0)]
    cases.append({'target':target,'value':value,'capacity_extra':cap_extra,'result':result,'calls':calls,'boundary':'modeled provider calls; source port uses actual pinned CCL; no Core original body recovery'})
 return cases

def parser_cases():
 import ctypes
 libc=ctypes.CDLL(None);libc.strcasecmp.argtypes=[ctypes.c_char_p,ctypes.c_char_p];libc.strcasecmp.restype=ctypes.c_int
 raw=ELF.read_bytes();j=json.loads((ROOT/'temp/recovery-work/graph-live-trial-08/batch03/packets/trial08_eq_7/native-context.json').read_text());b=j['bodies'][j['roots'][0]]
 scoped=json.loads((ROOT/'evidence/recovery/2026-11-02/dependency-graph/live-trial-08-10x10/scoped-data/eq.json').read_text())
 cases=[]
 for text in ['LowShelf','lowshelf','LOWSHELF','HighShelf','hIgHsHeLf','LowCut','lowcut','Peaking','PEAKING','','unknown','LowShelfX','High',' LowCut']:
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x290000);u.mem_write(b['address'],raw[b['file_offset']:b['file_offset']+b['size']]);u.mem_map(OBJ,0x20000);u.mem_map(STACK,0x10000);u.mem_map(STOP,0x1000)
  u.mem_write(1687576,raw[1654808:1654808+32])
  for r in scoped['ranges']:
   data=raw[r['file_offset']:r['file_offset']+r['size']];assert hashlib.sha256(data).hexdigest()==r['sha256'];u.mem_write(r['address'],data)
  u.mem_write(OBJ+0x1000,text.encode()+b'\0');calls=[]
  def cstr(addr):
   data=bytes(u.mem_read(addr,64));return data.split(b'\0')[0]
  def cb(uc,a,size,user):
   if a==0xa99c:
    left=cstr(uc.reg_read(UC_ARM_REG_R0));right=cstr(uc.reg_read(UC_ARM_REG_R1));result=libc.strcasecmp(left,right)
    calls.append({'left':left.decode(),'right':right.decode(),'equal':result==0});uc.reg_write(UC_ARM_REG_R0,result&0xffffffff);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,cb);u.reg_write(UC_ARM_REG_R0,OBJ);u.reg_write(UC_ARM_REG_R1,OBJ+0x1000);u.reg_write(UC_ARM_REG_SP,STACK+0x8000);u.reg_write(UC_ARM_REG_LR,STOP);u.emu_start(b['address'],STOP,count=1000);assert u.reg_read(UC_ARM_REG_PC)==STOP
  cases.append({'target':7,'text':text,'result':u.reg_read(UC_ARM_REG_R0),'calls':calls,'boundary':'actual host libc strcasecmp; original parser ARM and actual ELF table/strings'})
 return cases

if __name__=='__main__':
    groups={'fixtures.json':main(),'getter-fixtures.json':getter_cases(),'buffered-fixtures.json':buffered_cases(),'provider-fixtures.json':provider_composition_cases(),'parser-fixtures.json':parser_cases()}
    for name,cases in groups.items():
        expected=json.loads((ROOT/'uc-library/tests/recovery/trial08/eq'/name).read_text())['cases']
        assert cases==expected,name
    print(f"{sum(map(len,groups.values()))} original ARM executions freshly reproduced")
