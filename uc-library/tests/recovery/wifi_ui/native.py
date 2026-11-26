"""Original ARM WifiSetup target oracle; no host effects or Core body recovery."""
import importlib.util,pathlib,json,hashlib,struct,re
from unicorn.arm_const import *
ROOT=pathlib.Path(__file__).resolve().parents[4]
spec=importlib.util.spec_from_file_location('frozen_manager',ROOT/'uc-library/tests/recovery/wifi_manager/native.py');manager=importlib.util.module_from_spec(spec);spec.loader.exec_module(manager)
CONTEXT=ROOT/'temp/recovery-work/wifi-ui-sol61/CONTEXT.json'
class Oracle(manager.Network):
 def __init__(self):
  super().__init__('client',{});self.ui=0x10050000;self.write(self.ui,b'\0'*0x600);self.parameters={};self.parameter_info=[];self.param_values={};self.trace=[];self.ssid='Studio';self.password='';self.joins=[]
  context=json.loads(CONTEXT.read_text());symbol_table=self.elf.get_section_by_name('.symtab')
  for task in context['tasks']:
   for record in task['originals']:
    o=record['original'];symbols=symbol_table.get_symbol_by_name(o['mangled']);assert any((s['st_value'],s['st_size'],s['st_shndx'])==(o['address'],o['size'],o['section']) for s in symbols);off=self.elf.get_section(o['section'])['sh_offset']+o['address']-self.elf.get_section(o['section'])['sh_addr'];assert off==o['file_offset'] and self.raw[off:off+o['size']].hex()==o['range_hex'] and hashlib.sha256(self.raw[off:off+o['size']]).hexdigest()==o['range_sha256'];self.records.append(o);self.targets[o['mangled']]=o
  self.put(0x10070000+0x58,0x10071000);self.put(0x10070000+0x70,0x10071004)
 def info(self,a):
  b=bytes(self.u.mem_read(a,84));w=struct.unpack('<21I',b)
  return {'type':w[0],'tag':w[1],'name':b[8:40].split(b'\0')[0].decode(),'numeric':list(struct.unpack('<5f',b[40:60])),'flags':w[15],'text':[self.string(x) if x else None for x in w[16:18]],'initial_strings':[self.string(self.get(w[18]))] if w[18] else None,'title':self.string(w[19]) if w[19] else None,'short_title':self.string(w[20]) if w[20] else None}
 def hook(self,u,a,size,_):
  r=[u.reg_read(x) for x in manager.REG];name=next((n for n in self.names.get(a,[]) if not n.startswith('$')),None)
  if a==self.entry:return
  if a==0x10071000:self.param_values[self.get(r[0]+4)]=r[1];self.trace.append(['setValue',self.get(r[0]+4),r[1],r[2]]);self.ret();return
  if a==0x10071004:self.copystr(r[1],self.password,r[2]);self.trace.append(['toString',self.get(r[0]+4),r[2]]);self.ret();return
  if name=='memset':self.write(r[0],bytes([r[1]&255])*r[2]);self.ret(r[0]);return
  if name and 'PageComponentC' in name:self.trace.append(['page-construct',self.string(r[1]),self.string(r[2]),r[3]]);self.copystr(self.ui+8,self.string(r[1]),64);self.ret(self.ui);return
  if name and 'DelayTimerC' in name:self.trace.append(['timer-construct',struct.unpack('<f',struct.pack('<I',r[1]))[0]]);self.ret(r[0]);return
  if name and 'DelayTimerD' in name:self.trace.append(['timer-destroy']);self.ret(r[0]);return
  if name and 'ParamList3addEPKNS0_9ParamInfoEib' in name:
   entries=[]
   for i in range(r[2]):
    info=self.info(r[1]+84*i);entries.append(info);p=self.alloc(64);self.put(p,0x10070000);self.put(p+4,info['tag']);self.parameters[info['tag']]=p;self.parameter_info.append(info)
   self.trace.append(['parameters',r[2],r[3],entries]);self.ret();return
  if name and 'Component17getParameterByTagEi' in name:self.ret(self.parameters[r[1]]);return
  if name and 'Parameter17setFeedbackNeededEb' in name:self.trace.append(['feedback',self.get(r[0]+4),r[1]]);self.ret();return
  if name and 'WIFIManager11addDelegateE' in name:self.trace.append(['delegate-add']);return
  if name and 'WIFIManager14removeDelegateE' in name:self.trace.append(['delegate-remove']);return
  if name and 'WIFIManager6doScanEb' in name:self.trace.append(['scan',r[1]]);return
  if name and 'WIFIManager6doJoinE' in name:self.trace.append(['join',self.string(r[1]),self.string(r[2])]);self.joins.append([self.string(r[1]),self.string(r[2])]);return
  if name and 'WifiSetupComponent15getSelectedSSID' in name:self.copystr(r[1],self.ssid,64);self.trace.append(['selected-ssid',self.ssid]);self.ret();return
  if name and 'ComponentD2Ev' in name:self.trace.append(['component-destroy']);self.ret(r[0]);return
  if name and name.startswith('_ZdlPv') and r[0]==self.ui:self.trace.append(['delete-ui']);self.ret();return
  if name and 'BackgroundWorker7addTask' in name:
   v=self.get(r[1]);kind=next((k for k in ['ScanWIFITask','ActiveNetworkTask','JoinNetworkTask'] if self.symbols.get('_ZTVN8Presonus11WIFIManager'+str(len(k))+k+'E',0)+8==v),'unknown');self.trace.append(['queued',kind]);self.ret();return
  super().hook(u,a,size,_)
 def construct(self,variant='C1'):
  name=next(n for n in self.targets if 'WifiSetupComponent'+variant+'E' in n);self.copystr(0x10060000,'wireless-form',64);self.call(name,[self.ui,0x10060000,42]);return name
 def seed(self):
  items=[]
  for name in ['Studio','wifi']:
   p=self.alloc(320);self.copystr(p+0xc0,'[ESS]',64);self.copystr(p+0x100,name,64);items.append(p)
  array=self.alloc(8)
  for i,p in enumerate(items):self.put(array+4*i,p)
  self.put(self.obj+0x234,array);self.put(self.obj+0x238,2);self.put(self.obj+0x23c,2)
def generate():
 rows=[]
 for variant in ['C1','C2']:
  q=Oracle();q.seed();name=q.construct(variant);rows.append({'method':'constructor','mangled':name,'trace':q.trace,'parameters':q.parameter_info,'offset':q.get(q.ui+0x118),'selected':q.get(q.ui+0x11c),'delegates':q.get(q.obj+0x24c)})
 for variant in ['D0','D1','D2']:
  q=Oracle();q.seed();q.construct();name=next(n for n in q.targets if 'WifiSetupComponent'+variant+'Ev' in n);q.call(name,[q.ui]);rows.append({'method':'destructor','mangled':name,'trace':q.trace,'delegates':q.get(q.obj+0x24c)})
 q=Oracle();q.seed();q.construct();q.copystr(q.ui+0xd8,'previous',64);q.param_values[0]=0x3f800000;name=next(n for n in q.targets if 'WifiSetupComponent10disconnect' in n);q.call(name,[q.ui]);rows.append({'method':'disconnect','mangled':name,'trace':q.trace,'text':q.string(q.ui+0xd8),'parameter_value_bits':q.param_values[0]})
 for cancel in [False,True]:
  for password in ['','secret','secret ','secret  ',' ','x'*62+' ','x'*80]:
   q=Oracle();q.seed();q.construct();q.password=password;name=next(n for n in q.targets if 'WifiSetupComponent17textInputFinished' in n);q.call(name,[q.ui,int(cancel)]);rows.append({'method':'textInputFinished','mangled':name,'cancel':cancel,'password':password,'trace':q.trace})
 return {'version':1,'producer_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'context_sha256':hashlib.sha256(CONTEXT.read_bytes()).hexdigest(),'cases':rows,'domain':'Original full selected UI constructor/destructor/action instruction ranges; actual original manager add/remove/scan/join bodies execute over controlled Core/parameter/page/timer boundaries. Existing getSelectedSSID is an explicit controlled app dependency. No host effects/Core binary bodies.'}
if __name__=='__main__':
 d=generate();pathlib.Path(__file__).with_name('fixtures.json').write_text(json.dumps(d,indent=2)+'\n');print('native UI cases',len(d['cases']))
