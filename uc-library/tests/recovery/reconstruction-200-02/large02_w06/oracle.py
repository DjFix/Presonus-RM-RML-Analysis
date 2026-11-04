"""Execute exact original app ranges only. Core/libc/app dependencies are explicit stubs.
Native writes, calls, arguments and bounded projections are recorded independently
of proposed C++. This is neither a firmware execution environment nor ARM ABI proof.
"""
import argparse, hashlib, json, struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ELF = Path('rootfs/RML16AI_Rack_13731/home/root/mixer')
PACKETS = Path('temp/recovery-work/reconstruction-200-02/isolated-batch01/packets')
ELFHASH='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
REGS=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
THIS=0x9000000; MIXER=THIS+0x1000; CHANNEL=THIS+0x2000; ATTR=THIS+0x3000
CACHE=THIS+0x4000; PARAM=THIS+0x5000; HEAP=THIS+0x10000; VT=THIS+0x18000
STOP=0x8000000; STUB=0x8001000; STACK=0xa000000

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def cases():
 out=[]
 for n in range(1,20):
  variants=range(3) if n in [2,3,6,8,14,16,17,18,19] else range(3) if n==7 else range(2) if n in [4,5,15] else range(1)
  for v in variants:
   out.append({'id':f'{n:02}-{v}','method':n,'variant':v})
 return out

def run(case):
 n,v=case['method'],case['variant']; p=PACKETS/f'large02_w06_{n:02}'
 request=json.loads((p/'request.json').read_text()); original=request['originals'][0]['original']
 start,size=original['address'],original['size']
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
 with ELF.open('rb') as stream:
  ef=ELFFile(stream)
  sections=list(ef.iter_sections()); sec=sections[int(original['section_json'])]
  offset=sec['sh_offset']+start-sec['sh_addr'];stream.seek(offset);body=stream.read(size)
  assert len(body)==size
  expected=json.loads((p/'native-context.json').read_text())
  root=expected['roots'][0]; metadata=expected['nodes'][root]['metadata']
  # Verify section/range separately for every identity, including D0/D1.
  import re
  recorded=re.search(r'section \.text; SHA256 `([0-9a-f]{64})`', (p/'ELF_CONTEXT.md').read_text()).group(1)
  assert hashlib.sha256(body).hexdigest()==recorded
  for segment in ef.iter_segments():
   if segment['p_type']!='PT_LOAD':continue
   a=segment['p_vaddr']; lo=a&~4095; end=(a+segment['p_memsz']+4095)&~4095
   try:u.mem_map(lo,end-lo)
   except Exception:pass
   u.mem_write(a,segment.data())
 u.mem_map(THIS,0x20000);u.mem_map(STACK,0x20000);u.mem_map(STOP,0x10000)
 def put(a,x):u.mem_write(a,struct.pack('<I',x&0xffffffff))
 def word(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 def text(a):return bytes(u.mem_read(a,512)).split(b'\0',1)[0].decode('utf-8')
 def string(a,s):u.mem_write(a,s.encode()+b'\0')
 def get(i):return u.reg_read(REGS[i])
 def ret(x=None):
  if x is not None:u.reg_write(UC_ARM_REG_R0,x&0xffffffff)
  u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 stubs={};trace=[];writes=[];observed={};nextstub=STUB;executed={}
 def stub(name,fn):
  nonlocal nextstub
  a=nextstub;nextstub+=4;stubs[a]=(name,fn);return a
 paramtext={};params={};nextparam=PARAM
 def parameter(owner,tag,initial):
  nonlocal nextparam
  a=nextparam;nextparam+=0x100;params[owner,tag]=a;paramtext[a]=initial
  put(a,VT+0x500);put(a+12,a+0x80);put(a+0x84,tag)
  return a
 def lookup():ret(params.get((get(0),get(1)),0))
 numeric_values={}
 def value():ret(struct.unpack('<I',struct.pack('<f',numeric_values.get(get(0),float(([1,0,3.75] if n==7 else [-2.75,0,3.75])[v%3]))))[0])
 def setvalue():numeric_values[get(0)]=struct.unpack('<f',struct.pack('<I',get(1)))[0];ret()
 def tostring():string(get(1),paramtext[get(0)][:get(2)-1]);ret()
 def fromstring():paramtext[get(0)]=text(get(1));ret(1)
 put(VT+0x500+0x58,stub('Parameter::setValue',setvalue))
 put(VT+0x500+0x44,stub('Parameter::getValue',value));put(VT+0x500+0x70,stub('Parameter::toString',tostring));put(VT+0x500+0x74,stub('Parameter::fromString',fromstring))
 put(THIS,VT);put(MIXER,VT+0x100);put(CHANNEL,VT+0x200)
 put(THIS+0xc4,MIXER);put(THIS+0xe0,MIXER);put(THIS+0x8c,parameter(THIS,0,'0'))
 parameter(THIS,1,'Preset');parameter(THIS,2,'Edit');parameter(THIS,3,(['User','','U'*255][v%3] if n==2 else 'User'));parameter(THIS,100,'Cat');parameter(CHANNEL,2,(['Channel','','C'*255][v%3] if n==3 else 'Channel'))
 if not(n==8 and v==0):parameter(MIXER,13,'0')
 selection=parameter(MIXER,77,'0');put(THIS+0xc8,selection if n==5 and v==1 else (params[THIS,100] if n==19 and v!=0 else 0))
 put(MIXER+0x2b0,MIXER+0x400);put(MIXER+0x2b4,1);put(MIXER+0x400,CHANNEL if v==0 else 0)
 newpath='02.Edit.Cat.channel';oldpath=['02.* Empty Location *.channel',newpath,'02.Old.Cat.channel'][v%3]
 if n==16:newpath='02.Edit.scene';oldpath=['02.* Empty Location *.scene',newpath,'02.Old.scene'][v%3]
 def base_recalled():observed['recalled']=1;ret()
 def base_stored():observed['stored']=1;ret()
 def base_update():ret()
 def update_edit():paramtext[params[THIS,2]]=paramtext[params[THIS,1]];ret()
 def load():
  observed['loaded']=1;observed['mode']=text(get(1));ret(1 if v==0 else 0)
 def save():observed['saved']=1;observed['mode']=text(get(1));ret(1)
 def save_username():paramtext[params[CHANNEL,2]]=paramtext[params[THIS,3]];observed['username_saved']=1;ret(1)
 put(VT+0x30,stub('ChannelPresetComponent::saveUserName',save_username));put(VT+0x200+0x20,stub('Component::load',load));put(VT+0x200+0x24,stub('Component::save',save))
 put(VT+0x100+0x80,stub('Mixer::filter',lambda:ret(0)))
 def cache_build():string(get(0),newpath);ret(get(0))
 def oldfile():string(get(0),oldpath);ret(get(0))
 def cache():observed['cache_name']=text(get(1));observed['cache_category']=text(get(2));observed['cache_slot']=get(3);ret()
 def do_save():observed['save_name']=text(get(1));observed['save_category']=text(get(2));ret()
 def scene():observed['scene']=1;observed['notify']=get(3);ret(0) # caller ignores failure
 def deleting():observed['deleted']=1;ret()
 def base_dtor():
  observed['base_cleanup']=1;observed['native_base_entry_words']=[word(THIS),word(THIS+4),word(THIS+0x84)];ret()
 def new():observed['allocation_size']=get(0);ret(HEAP)
 def strcmp():ret(0 if text(get(0))==text(get(1)) else 1)
 def deletedfile():observed['old_deleted']=int(v==2);observed['old_delete_requested']=text(get(0));ret(int(v==2))
 def background():observed['background']=1;observed['output_file']=text(get(0));ret(1)
 def slot():ret(0 if n==16 and v==0 else 1)
 def soft_float():ret(int(struct.unpack('<f',struct.pack('<I',get(0)))[0]))
 def cstring():string(get(0),text(get(1)) if get(1) else '');ret(get(0))
 def allocate():ret(HEAP+0x1000)
 def empty():ret()
 def setselection():observed['selected']=get(1);ret()
 def categorychanged():observed['category_changed']=1;ret()
 bindings={0x2f3fc:('Mixer::selectedChannel',lambda:ret(CHANNEL)),0x119c4c:('Component::getParameterByTag',lookup),0x8388c:('Preset::updatePresetName',base_update),0xbc80:('CString256::constructor',cstring),0x157958:('float-to-int',soft_float),0x837a4:('Preset::presetRecalled',base_recalled),0x8359c:('unused',empty),0x83498:('Preset::getSlotNum',slot),0x83cac:('Preset::getCache',lambda:ret(CACHE)),0x85764:('Cache::buildFileName',cache_build),0x83de0:('Preset::getFileNameForSlot',oldfile),0x35fa8:('Mixer::saveScene',scene),0x857d4:('Cache::cachePreset',cache),0x834c0:('Preset::presetStored',base_stored),0xaf70:('strcmp',strcmp),0x127998:('FileUtils::deleteFile',deletedfile),0x118ec8:('ArchiveUtils::saveInBackground',background),0x83650:('Preset::createStorageHandler',lambda:ret(HEAP)),0x84348:('Preset::~Preset',base_dtor),0xac10:('operator delete',deleting),0xa7e4:('operator new',new),0x839b4:('Preset::paramChanged',empty),0x3a06c:('Channel::categoryChanged',categorychanged),0x39ce8:('Channel::setChannelIndex',setselection),0x836dc:('Preset::updateEditName',update_edit),0x121dbc:('AttributeAllocator::getDefault',allocate),0x121a68:('Attributes::constructor',empty),0x117950:('AttributesBuilder::constructor',empty),0x2f178:('Vector::~Vector',empty),0x1228b0:('Attributes::~Attributes',empty),0x83f3c:('Preset::doPresetSave',do_save)}
 for a,(name,fn) in bindings.items():
  if not start<=a<start+size:stubs[a]=(name,fn)
 # Execute the expanded app base destructor too; source-provided Core remains
 # trapped. Existing manager/no-cache and cache-observer removal are separate.
 allowed=[(start,start+size)]
 if n==7:
  del stubs[0x3a06c];del stubs[0x39ce8]
  allowed.extend([(0x3a06c,0x3a06c+268),(0x39ce8,0x39ce8+64)])
  gate=parameter(THIS,78,'0');put(THIS+0x88,gate);put(THIS+0xc8,params[THIS,100])
  allowed.append((0x39c5c,0x39c5c+140))
  put(4799580,1) # function-static initialization already completed
  assert hashlib.sha256(bytes(u.mem_read(0x39c5c,140))).hexdigest()=='29a721a32d838410802046be26e3b393edacbced7a76e0f2b7f72fb16b421042'
  def cache_info():
   index=get(3)
   assert index < 0x80000000,'negative native cache index outside domain'
   if index>=10:ret(0);return
   string(get(1),'Old' if index==1 and v==2 else 'Edit' if index==1 and v==1 else '* Empty Location *')
   string(get(2),'Cat' if index==1 and v in [1,2] else '')
   ret(1)
  def strlen():ret(len(text(get(0))))
  def strncpy():u.mem_write(get(0),bytes(u.mem_read(get(1),get(2))));ret(get(0))
  def fcmp():ret(int(struct.unpack('<f',struct.pack('<I',get(0)))[0]>0))
  def tofloat():ret(struct.unpack('<I',struct.pack('<f',float(get(0))))[0])
  stubs.update({0x85bac:('PresetNameCache::getPresetInfo boundary',cache_info),0xae98:('strlen',strlen),0xafe8:('strncpy',strncpy),0x157940:('float compare',fcmp),0x15746c:('uint-to-float',tofloat)})
 if n in [1,9,10,11,12,13]:
  del stubs[0x84348]
  allowed.append((0x84348,0x84348+396))
  assert hashlib.sha256(bytes(u.mem_read(0x84348,396))).hexdigest()=='8d768fa18a273dabe49a2142e70726ac74b02d7fda75db14d4ba151aaabc4663'
  observed['base_cleanup']=0
  put(0x494c0c,MIXER) # manager singleton literal at 0x844c8
  put(CACHE+0x150,CACHE+0x400);put(CACHE+0x154,3)
  put(CACHE+0x400,THIS+0x84);put(CACHE+0x404,THIS+0x800);put(CACHE+0x408,THIS+0x804)
  stubs[0x84b08]=('PresetNameManager::lookupCache',lambda:ret(CACHE))
  stubs[0x84608]=('Core::Vector::~Vector source boundary',empty)
  stubs[0x11a53c]=('Core::Component::~Component source boundary',empty)
 def hook(uc,a,sz,user):
  if a==STOP:uc.emu_stop();return
  executed[a]=executed.get(a,0)+1
  if a in stubs:
   name,fn=stubs[a];trace.append({'call':name,'address':a,'args':[get(i) for i in range(4)]});fn();return
  if a==0x84348 and n in [1,9,10,11,12,13]:observed['base_cleanup']+=1
  if not any(lo<=a<hi for lo,hi in allowed):raise RuntimeError(f'unbound external execution {a:x} in method {n}')
 def writing(uc,access,a,sz,val,user):
  if THIS<=a<THIS+0x20000:writes.append({'region':'fixture_heap','address':a-THIS,'absolute_address':a,'size':sz,'value':val})
  elif 4799580<=a<4799584+32:writes.append({'region':'static_category','absolute_address':a,'size':sz,'value':val})
 u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,writing)
 sp=STACK+0x18000;u.reg_write(UC_ARM_REG_SP,sp);u.reg_write(UC_ARM_REG_LR,STOP)
 for i,x in enumerate([THIS,ATTR,1,0]):u.reg_write(REGS[i],x)
 if n==17:
  string(ATTR,'Edit');string(ATTR+0x100,'Cat');u.reg_write(UC_ARM_REG_R1,ATTR);u.reg_write(UC_ARM_REG_R2,ATTR+0x100);u.reg_write(UC_ARM_REG_R3,ATTR+0x200)
 if n==18:
  string(ATTR,'Updated');string(ATTR+0x100,'NewCat');u.reg_write(UC_ARM_REG_R1,CACHE);u.reg_write(UC_ARM_REG_R2,1 if v else 9);u.reg_write(UC_ARM_REG_R3,ATTR);put(sp,ATTR+0x100)
 if n==7:
  a=params[THIS,0 if v==0 else 100];u.reg_write(UC_ARM_REG_R1,a);u.reg_write(UC_ARM_REG_R2,2)
 if n==14:
  put(THIS+0xe8,ATTR if v else 0);string(ATTR+0x88,'reverb' if v==1 else 'delay')
 u.emu_start(start,STOP+4,count=10000)
 assert u.reg_read(UC_ARM_REG_PC)==STOP,'instruction budget exhausted'
 if n==4:
  allowed.append((0x844d4,0x844d4+24))
  assert hashlib.sha256(bytes(u.mem_read(0x844d4,24))).hexdigest()=='2bf437e365e3e516205aaf02037f388eabe9e58914e42fc6ebf63d99ba706e5a'
  u.reg_write(UC_ARM_REG_R0,HEAP);u.reg_write(UC_ARM_REG_R1,ATTR);u.reg_write(UC_ARM_REG_SP,sp);u.reg_write(UC_ARM_REG_LR,STOP)
  u.emu_start(0x844d4,STOP+4,count=1000)
  assert u.reg_read(UC_ARM_REG_PC)==STOP
 result=u.reg_read(UC_ARM_REG_R0);result=result-(1<<32) if result&(1<<31) else result
 projection={}
 if n in [1,9,10,11,12,13]:projection={'base_cleanup':observed['base_cleanup'],'deleted':observed.get('deleted',0),'cache_observers_remaining':word(CACHE+0x154)}
 elif n==2:projection={'result':result,'channel_name':paramtext[params[CHANNEL,2]]}
 elif n==3:projection={'user_name':paramtext[params[THIS,3]]}
 elif n==4:projection={'owner_bound':int(word(HEAP+4)==THIS),'completion_stored':observed.get('stored',0)}
 elif n in [5,15]:projection={'result':result,'loaded':observed.get('loaded',0),'recalled':observed.get('recalled',0),'mode':observed.get('mode','')}
 elif n in [6,8]:projection={'result':result}
 elif n==7:projection={'category':paramtext[params[THIS,100]],'slot':int(numeric_values.get(params[THIS,0],float(([1,0,3.75] if n==7 else [-2.75,0,3.75])[v%3])))}
 elif n==14:projection={'type':text(u.reg_read(UC_ARM_REG_R0))}
 elif n in [16,17]:projection={k:observed.get(k,0) for k in ['stored','old_deleted']};projection.update({'result':result} if n==16 else {});projection.update({k:observed[k] for k in ['cache_name','cache_category','cache_slot'] if k in observed});projection['scheduled']=observed.get('scene',observed.get('background',0))
 elif n==18:projection={'name':paramtext[params[THIS,1]],'category':paramtext[params[THIS,100]],'edit':paramtext[params[THIS,2]]}
 elif n==19:projection={'result':result,'saved':observed['saved'],'mode':observed['mode'],'name':observed['save_name'],'category':observed['save_category'],'username_saved':observed['username_saved']}
 dependencies=[]
 descriptors={
 0x84348:('_ZN8Presonus5Panel15PresetComponentD2Ev',396,'8d768fa18a273dabe49a2142e70726ac74b02d7fda75db14d4ba151aaabc4663'),
 0x3a06c:('_ZN8Presonus5Panel22ChannelPresetComponent23onPresetCategoryChangedEv',268,'705dc27c86d85e32e46a0c6b35428202f955f770f95eac93d77a4c2d7703180b'),
 0x39ce8:('_ZN8Presonus5Panel22ChannelPresetComponent19onSlotNumberChangedEi',64,'b8a8c02275bfa94fbe737538374d78b192eaec41bcfc27aa0ac21a71c724abdf'),
 0x39c5c:('_ZN8Presonus5Panel22ChannelPresetComponent11getCategoryEi',140,'29a721a32d838410802046be26e3b393edacbced7a76e0f2b7f72fb16b421042'),
 0x844d4:('_ZN8Presonus5Panel15PresetComponent24StorageCompletionHandler19onSaveFileCompletedEPKc',24,'2bf437e365e3e516205aaf02037f388eabe9e58914e42fc6ebf63d99ba706e5a')}
 for address,end in allowed[1:]:
  name,length,h=descriptors[address];assert end==address+length
  assert hashlib.sha256(bytes(u.mem_read(address,length))).hexdigest()==h
  dependencies.append({'elf_sha256':ELFHASH,'firmware':'RM/RML mixer 13731','role':'server','mangled':name,'address':address,'size':length,'section':'.text','file_offset':sec['sh_offset']+address-sec['sh_addr'],'range_sha256':h,'executed_instruction_count':sum(count for pc,count in executed.items() if address<=pc<end),'primary_recovery_identity':False})
 return {'case':case,'projection':projection,'dependency_ranges':dependencies,'native_trace':trace,'native_writes':writes,'native_observations':observed,'range':{'elf_sha256':ELFHASH,'mangled':original['mangled'],'address':start,'size':size,'section':sec.name,'file_offset':offset,'range_sha256':hashlib.sha256(body).hexdigest()}}

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);args=parser.parse_args()
 assert sha(ELF)==ELFHASH
 result={'producer':str(Path(__file__)),'producer_sha256':sha(Path(__file__)),'unicorn_version':__import__('unicorn').__version__,'scope':'Exact primary app ranges plus explicitly supplied app dependency ranges; remaining external calls are named boundary stubs. No Core firmware execution or dependency readiness propagation.','cases':[run(c) for c in cases()]}
 Path(args.out).write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
