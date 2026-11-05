"""Native app attribute/setter instructions, opaque Core call boundaries recorded."""
from oracle import *

def generate_attributes():
 p=ROOT/'rootfs/CS18_v13840/home/root/surface';blob=p.read_bytes();assert sha(blob)=='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0';elf=ELFFile(io.BytesIO(blob));ranges=[]
 for n in ['c10_02','c10_03','c10_04']:
  c=json.loads((PACKETS/('rolling200_impl_'+n)/'context.json').read_text());b=next(iter(c['native_context']['bodies'].values()));sec=elf.get_section(b['section_index']);off=int(sec['sh_offset'])+b['address']-int(sec['sh_addr']);assert off==b['file_offset'];assert sha(blob[off:off+b['size']])==b['bytes_sha256'];ranges.append(dict(task=n,address=b['address'],size=b['size'],section=sec.name,file_offset=off,sha256=b['bytes_sha256']))
 cases=[];executed=set()
 for names,controller,results,images in itertools.product(itertools.product(range(3),repeat=2),[0,1],itertools.product(range(3),repeat=2),itertools.product(range(3),repeat=2)):
  sn,dn=names;sr,dr=results;old,new=images;case=[4,sn,dn,controller,sr,dr,old,new];u=unicorn.Uc(unicorn.UC_ARCH_ARM,unicorn.UC_MODE_ARM);pages=set()
  for seg in elf.iter_segments():
   if seg['p_type']!='PT_LOAD':continue
   a=int(seg['p_vaddr']);n=int(seg['p_memsz'])
   for page in range(a&~4095,(a+n+4095)&~4095,4096):
    if page not in pages:u.mem_map(page,4096);pages.add(page)
   u.mem_write(a,seg.data())
  u.mem_map(OBJ,0x10000);u.mem_map(STACK,0x10000);u.mem_map(STOP,4096);u.mem_write(OBJ,bytes([0xa5])*512)
  def wp(a,v):u.mem_write(a,word(v))
  def rp(a):return struct.unpack('<I',u.mem_read(a,4))[0]
  def image(i):return 0 if not i else OBJ+0x6000+i*0x100
  wp(OBJ+0x58,image(old));wp(OBJ+0x5c,OBJ+0x4000 if controller else 0);wp(OBJ+0x60,0);wp(OBJ+0x64,0)
  # Native app sees a pre-acquired temporary from the opaque getBitmap boundary.
  for i in [1,2]:wp(image(i)+0x34,(1 if i==old else 0)+(1 if i==new else 0))
  wp(OBJ+0x4000,OBJ+0x5000);wp(OBJ+0x500c,STOP+0x100)
  u.mem_write(OBJ+0x8000,b'\0');u.mem_write(OBJ+0x8100,b'first\0');u.mem_write(OBJ+0x8200,b'second\0')
  u.reg_write(UC_ARM_REG_SP,STACK+0xf000);u.reg_write(UC_ARM_REG_LR,STOP);u.reg_write(UC_ARM_REG_R0,OBJ);u.reg_write(UC_ARM_REG_R1,OBJ+0x9000);trace=[];pcs=[];writes=[]
  def string(a):return bytes(u.mem_read(a,32)).split(b'\0')[0].decode()
  def code(uc,a,size,data):
   r0=uc.reg_read(UC_ARM_REG_R0);r1=uc.reg_read(UC_ARM_REG_R1);r2=uc.reg_read(UC_ARM_REG_R2)
   if a==0xf8000:assert r0==OBJ and r1==OBJ+0x9000;trace.append('attributes-base')
   elif a==0x124200:
    name=string(r1);assert name in ['valuestyle','dot'];v=sn if name=='valuestyle' else dn;uc.reg_write(UC_ARM_REG_R0,0 if v==0 else OBJ+0x8000 if v==1 else OBJ+(0x8100 if name=='valuestyle' else 0x8200))
   elif a==STOP+0x100:
    assert r0==OBJ+0x4000 and string(r2)=='Param';name=string(r1);assert name in ['first','second'];trace.append('lookup:'+name);uc.reg_write(UC_ARM_REG_R0,ptr(sr if name=='first' else dr))
   elif a==0xf940c:assert r1==OBJ+0x9000 and string(r2)=='image';trace.append('bitmap');wp(r0,image(new))
   elif a in [0x11e2e0,0x11f4f0]:assert r1==OBJ+0x44;trace.append(('remove:' if a==0x11e2e0 else 'add:')+str((r0-OBJ)//0x1000))
   elif a==0x10e9fc:assert r0==OBJ;trace.append('invalidate')
   else:
    assert any(b['address']<=a<b['address']+b['size'] for b in ranges),hex(a);pcs.append(a);return
   uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  def mem(uc,access,a,size,value,data):
   if OBJ<=a<OBJ+0x10000:writes.append([a-OBJ,size,value])
  u.hook_add(unicorn.UC_HOOK_CODE,code);u.hook_add(unicorn.UC_HOOK_MEM_WRITE,mem);u.emu_start(ranges[0]['address'],STOP,count=1000);assert u.reg_read(UC_ARM_REG_PC)==STOP
  state=bytes(u.mem_read(OBJ,512));assert all(v==0xa5 for i,v in enumerate(state) if not 0x58<=i<0x68)
  vals=[rp(OBJ+0x60),rp(OBJ+0x64)];vals=[0 if not v else (v-OBJ)//0x1000 for v in vals];img=rp(OBJ+0x58);vals.append(0 if not img else (img-OBJ-0x6000)//0x100)
  # The app has consumed exactly one reference from the opaque temporary result.
  refs=[rp(image(i)+0x34) for i in [1,2]];assert refs==[int(new==i) for i in [1,2]],(case,refs)
  cases.append(dict(input=case,expected=dict(values=vals,trace=trace,writes=writes,image_reference_counts=refs)));executed.update(pcs)
 return dict(version=1,elf_sha256=sha(blob),ranges=ranges,cases=cases,executed_addresses=sorted(executed),oracle='Original app + exact assigned setters; Core calls are opaque boundary observations; nonnull bitmap temporary pre-acquired as explicit assumption. No Core instructions executed.')
if __name__=='__main__':Path(sys.argv[1]).write_text(json.dumps(generate_attributes(),indent=2)+'\n')
