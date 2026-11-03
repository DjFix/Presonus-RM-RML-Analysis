import pathlib,hashlib,json
from elftools.elf.elffile import ELFFile
path=pathlib.Path('rootfs/RML16AI_Rack_13731/home/root/mixer');data=path.read_bytes();assert hashlib.sha256(data).hexdigest()=='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07';rows=[]
with path.open('rb') as f:
 elf=ELFFile(f)
 for variant in ['C1','C2']:
  name='_ZN8Presonus12DspComponent'+variant+'EPKcPNS_3Dsp11IControllerE';matches=[s for s in elf.get_section_by_name('.symtab').iter_symbols() if s.name==name];assert len(matches)==1;s=matches[0];section=elf.get_section(s['st_shndx']);offset=section['sh_offset']+s['st_value']-section['sh_addr'];body=data[offset:offset+s['st_size']];assert s['st_value']==(0x82ab4 if variant=='C1' else 0x82afc) and s['st_size']==72;h=hashlib.sha256(body).hexdigest();assert variant!='C1' or h=='17cd118831b13c8018c932cb222086fc14be9e9e095d670548c1f093992f0f37';rows.append({'mangled':name,'address':s['st_value'],'size':s['st_size'],'section':s['st_shndx'],'offset':offset,'sha256':h,'selected':variant=='C1'})
print(json.dumps({'ranges':rows,'native_alias':False,'admission_only':'C1'},indent=2))
