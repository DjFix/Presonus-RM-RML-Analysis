import hashlib,json,struct,sys
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import *
from unicorn.arm_const import *
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent
ELF=ROOT/'rootfs/RML16AI_Rack_13731/home/root/mixer'
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
NAME='_ZN8Presonus4NOAA12TCardHandler11threadEntryEv'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 assert sha(ELF)==SHA
 with ELF.open('rb') as f:
  e=ELFFile(f);s=next(s for s in e.get_section_by_name('.symtab').iter_symbols() if s.name==NAME)
  assert (s['st_value'],s['st_size'],s['st_shndx'])==(652748,572,12)
  sec=e.get_section(12);off=sec['sh_offset']+s['st_value']-sec['sh_addr'];assert off==0x975cc
  f.seek(off);body=f.read(572);assert hashlib.sha256(body).hexdigest()=='c4294d686e9eb130a7d18ef64fc1a186f451b949839b89a51db8a4ab5c8131b5'
  segments=[(x['p_vaddr'],x.data()) for x in e.iter_segments() if x['p_type']=='PT_LOAD']
 cases=[dict(name='stopped',times=[],events=[],stopped=True),dict(name='deadlines',times=[-1,0,1,21,22,42,43],events=[]),dict(name='fifo-pools',times=[0]*7,events=[[100,16],[101,17],[102,32],[103,33],[104,512],None]),dict(name='cadence',times=[0]*65,events=[]),dict(name='lazy',times=[0],events=[],lazy=True),dict(name='signed-wide',times=[-9223372036854,-1,0,1,4294967297,4294967317,4294967318],events=[])]
 for c in cases:
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x600000)
  for a,b in segments:u.mem_write(a,b)
  base=0x1000000;u.mem_map(base,0x40000);obj=base;stack=base+0x38000;stop=base+0x3f000
  def wr(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
  def rd(a):return struct.unpack('<I',u.mem_read(a,4))[0]
  wr(obj+0x64,int(c.get('stopped',False)));wr(obj+0x6c,base+0x1000)
  u.mem_write(4805472,bytes(8));wr(4805480,0 if c.get('lazy') else base+0x2000)
  for i,pool in enumerate([4805368,4805400,4805432]):wr(pool,base+0x3000+i*0x100);wr(pool+12,20)
  n=len(c['events']);wr(obj+0xa4,base+0x4000 if n else 0);wr(obj+0xa8,base+0x4000+(n-1)*16 if n else 0)
  for i,event in enumerate(c['events']):
   node=base+0x4000+i*16;prop=base+0x6000+i*0x100
   wr(node,prop if event else 0);wr(node+4,node+16 if i+1<n else 0);wr(node+8,node-16 if i else 0)
   if event:wr(prop,event[0]);wr(prop+4,event[1])
  pcs=[];writes=[];calls=[];iteration=0;pending=[];nodes=[]
  boundaries={0xa15e0:'router',0xa38d0:'spi',0x10e948:'sleep',0x10e384:'lock',0x10e460:'unlock',0xac10:'delete',0x9e9e8:'dispatch',0x11677c:'push',0x116908:'clock',0x157a08:'divide',0xa7e4:'new',0xa2e64:'ctor',0x126cfc:'register'}
  def code(u,a,n,_):
   nonlocal iteration
   if a==stop:u.emu_stop();return
   if a in boundaries:
    name=boundaries[a];r=[u.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]]
    args=[]
    if name in ['lock','unlock']:args=['main' if r[0]==obj+0x70 else 'queue'];assert r[0] in [obj+0x70,obj+0x88]
    elif name=='delete':args=[(r[0]-(base+0x4000))//16];assert base+0x4000<=r[0]<base+0x4000+16*len(c['events'])
    elif name=='dispatch':assert r[0]==obj;args=[rd(r[1]),rd(r[1]+4)]
    elif name=='push':args=[r[0]-(base+0x3000),rd(r[1])];assert args[1]==0
    elif name=='spi':args=[r[1]]
    elif name=='sleep':
     assert r[0]==2;args=[2]
     head=rd(obj+0xa4);count=0;links=0
     while head:
      links+=1;count+=int(rd(head)!=0);head=rd(head+4)
     pending.append(count);nodes.append(links);iteration+=1
     if iteration==len(c['times']):wr(obj+0x64,1)
    elif name=='clock':
     value=c['times'][iteration]*1000000
     u.reg_write(UC_ARM_REG_R0,value&0xffffffff);u.reg_write(UC_ARM_REG_R1,(value>>32)&0xffffffff)
    elif name=='divide':
     value=r[0]|r[1]<<32;value=value-(1<<64) if value>>63 else value
     divisor=r[2]|r[3]<<32;assert divisor==1000000
     quotient=abs(value)//divisor*(1 if value>=0 else -1)
     u.reg_write(UC_ARM_REG_R0,quotient&0xffffffff);u.reg_write(UC_ARM_REG_R1,(quotient>>32)&0xffffffff)
    elif name=='new':assert r[0]==456;u.reg_write(UC_ARM_REG_R0,base+0x2000)
    elif name in ['ctor','register']:assert r[0]==base+0x2000
    if name not in ['clock','divide']:calls.append([name,args])
    u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
   assert 0x9f5cc<=a<0x9f7e4,hex(a)
   pcs.append(a)
  def write(u,access,a,n,v,_):
   assert (stack-0x100<=a and a+n<=stack) or (base<=a and a+n<=base+0x10000) or (4805368<=a and a+n<=4805484),(hex(a),n)
   writes.append([u.reg_read(UC_ARM_REG_PC),a,n,v])
  u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
  for reg,v in [(UC_ARM_REG_R0,obj),(UC_ARM_REG_SP,stack),(UC_ARM_REG_LR,stop)]:u.reg_write(reg,v)
  u.emu_start(0x9f5cc,stop,count=200000);assert u.reg_read(UC_ARM_REG_PC)==stop;assert u.reg_read(UC_ARM_REG_R0)==0
  c.update(calls=calls,pcs=pcs,writes=writes,pending_at_sleep=pending,nodes_at_sleep=nodes,final_deadline=struct.unpack('<q',u.mem_read(4805472,8))[0],pool_counts=[rd(p+12) for p in [4805368,4805400,4805432]])
 result=dict(elf=SHA,symbol=NAME,address=652748,size=572,section=12,file_offset=off,range_sha256=hashlib.sha256(body).hexdigest(),oracle_sha256=sha(Path(__file__)),unicorn=__import__('unicorn').__version__,cases=cases)
 text=json.dumps(result,indent=2)+'\n';p=OUT/'fixtures.json'
 if '--verify' in sys.argv:assert p.read_text()==text
 else:p.write_text(text)
 lines=[]
 for c in cases:
  if c.get('lazy'):continue
  calls=c['calls'];idle=[sum(1 for name,args in calls[:i] if name=='sleep') for i,(name,args) in enumerate(calls) if name=='router'];spi=[args[0] for name,args in calls if name=='spi']
  dispatch=[args[0] for name,args in calls if name=='dispatch']
  lines.append(' '.join(map(str,[c['name'],len(c['times']),*c['times'],len(idle),*idle,len(spi),*spi,len(dispatch),*dispatch,*c['pending_at_sleep'],*c['nodes_at_sleep']])))
 p=OUT/'stdin.txt';text='\n'.join(lines)+'\n'
 if '--verify' in sys.argv:assert p.read_text()==text
 else:p.write_text(text)
 print('PASS6 exact ARM cases; guarded PCs/writes/imports; original nested dispatch lock retained in fixture')
if __name__=='__main__':main()
