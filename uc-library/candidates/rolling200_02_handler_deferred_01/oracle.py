import hashlib,json,struct,sys
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import *
from unicorn.arm_const import *
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).parent
ELF=ROOT/'rootfs/RML16AI_Rack_13731/home/root/mixer'
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
NAME='_ZN8Presonus4NOAA12TCardHandler19setPropertyDeferredERKN4Core8PropertyE'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 assert sha(ELF)==SHA
 with ELF.open('rb') as f:
  e=ELFFile(f);s=next(s for s in e.get_section_by_name('.symtab').iter_symbols() if s.name==NAME)
  assert (s['st_value'],s['st_size'],s['st_shndx'])==(649704,596,12)
  sec=e.get_section(12);off=sec['sh_offset']+s['st_value']-sec['sh_addr'];assert off==0x969e8
  f.seek(off);body=f.read(596);assert hashlib.sha256(body).hexdigest()=='659c745b1e2d5d59cec2785908a9307b24c5fcb0c3aa8f46842e15bc8d44fb62'
  segments=[(x['p_vaddr'],x.data()) for x in e.iter_segments() if x['p_type']=='PT_LOAD']
 assert struct.unpack('<6I',body[-24:])==(1634038640,1936225136,1399157877,0x472fc800,0x473f6800,0x47afc800)
 cases=[dict(kind=0,words=[0]*6),dict(kind=1,words=[0]*6)]
 for bits in [0,0x7fc00000,0x7f800000,0xff800000]+[t+d for t in [0x472fc800,0x473f6800,0x47afc800] for d in [-1,0,1]]:
  cases.append(dict(kind=2,words=[bits,0,0,0,0,0xfffffff3]))
 for start,counts in [(0,[0,0,0,0]),(0,[-1,-2,-3,-4]),(0,[2,2,2,2]),(254,[3,2,2,2]),(0,[260,0,0,0]),(0,[0,0,0,1]),(52,[1,1,1,1])]:
  cases.append(dict(kind=3,words=[start,*[x&0xffffffff for x in counts],0]))
 cases.append(dict(kind=2,words=[0,0,0,0,0,0],invalid_size=True))
 for c in cases:
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x600000)
  for a,b in segments:u.mem_write(a,b)
  base=0x1000000;u.mem_map(base,0x20000);obj=base;prop=base+0x1000;stack=base+0x18000;stop=base+0x1f000
  def wr(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
  def rd(a):return struct.unpack('<I',u.mem_read(a,4))[0]
  wr(obj+0x68,base+0x3000);wr(obj+0x6c,base+0x4000)
  wr(prop,[0,1936225136,1399157877,1634038640][c['kind']]);wr(prop+4,39 if c.get('invalid_size') else 40)
  if c['kind']==2:wr(prop+8,c['words'][0]);wr(prop+0x1c,c['words'][5])
  if c['kind']==3:
   for o,v in zip([8,0x10,0x18,0x1c,0x20],c['words'][:5]):wr(prop+o,v)
  pcs=[];writes=[];calls=[]
  boundaries={0x1578f8:'fcmplt',0xa17d8:'initRoutes',0xa0f50:'setAVS48Route',0x9ddd4:'sendSampleRate',0x9e85c:'sendGEQBulkProperty'}
  def code(u,a,n,_):
   if a==stop:u.emu_stop();return
   if a in boundaries:
    name=boundaries[a];r=[u.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]]
    if name=='fcmplt':
     x,y=[struct.unpack('<f',struct.pack('<I',v))[0] for v in r[:2]];u.reg_write(UC_ARM_REG_R0,int(x<y))
    else:
     args=r[1:] + ([rd(u.reg_read(UC_ARM_REG_SP))] if name=='setAVS48Route' else [])
     if name=='initRoutes':args=[]
     if name=='sendGEQBulkProperty':assert r[:2]==[obj,prop];args=[]
     calls.append([name,args]);u.reg_write(UC_ARM_REG_R0,0)
    u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
   assert 0x9e9e8<=a<0x9ec24,hex(a)
   pcs.append(a)
  def write(u,access,a,n,v,_):
   assert stack-0x100<=a and a+n<=stack,(hex(a),n)
   writes.append([u.reg_read(UC_ARM_REG_PC),a-stack,n,v])
  u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
  for reg,v in [(UC_ARM_REG_R0,obj),(UC_ARM_REG_R1,prop),(UC_ARM_REG_SP,stack),(UC_ARM_REG_LR,stop)]:u.reg_write(reg,v)
  try:
   u.emu_start(0x9e9e8,stop,count=200000)
   assert not c.get('invalid_size')
   assert u.reg_read(UC_ARM_REG_PC)==stop
  except UcError as error:
   assert c.get('invalid_size') and u.reg_read(UC_ARM_REG_PC)==0x9ea90 and error.errno==UC_ERR_READ_UNMAPPED
   c['native_fault']='read unmapped address0x1c at0x9ea90; size40 is a native precondition'
  c.update(calls=calls,pcs=pcs,writes=writes)
 result=dict(elf=SHA,symbol=NAME,address=649704,size=596,section=12,file_offset=off,range_sha256=hashlib.sha256(body).hexdigest(),oracle_sha256=sha(Path(__file__)),unicorn=__import__('unicorn').__version__,cases=cases)
 p=OUT/'fixtures.json'
 if '--verify' in sys.argv:assert json.loads(p.read_text())==result
 else:p.write_text(json.dumps(result,indent=2)+'\n')
 lines=[]
 for c in cases:
  if c.get('invalid_size'):continue
  calls=[x for x in c['calls'] if x[0]=='setAVS48Route'];rate=next((x[1][0] for x in c['calls'] if x[0]=='sendSampleRate'),0)
  lines.append(' '.join(map(str,[c['kind'],*c['words'],rate,len(calls),*[v for _,args in calls for v in args]])))
 p=OUT/'stdin.txt';text='\n'.join(lines)+'\n'
 if '--verify' in sys.argv:assert p.read_text()==text
 else:p.write_text(text)
 print('PASS exact ARM target',len(cases),'private-memory cases; PC/write guards; named boundaries')
if __name__=='__main__':main()
