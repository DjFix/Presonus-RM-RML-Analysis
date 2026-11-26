"""Prepare-only host symbol mapper for owner-approved retained static helpers.
This script is not executed by proof preparation. It maps actual built inputs,
never extracts/reconstructs a production body or fabricates a symbol/export.
"""
import argparse,hashlib,json,pathlib,subprocess
from io import BytesIO
from elftools.elf.elffile import ELFFile
p=argparse.ArgumentParser();p.add_argument('binary',type=pathlib.Path);p.add_argument('out',type=pathlib.Path);p.add_argument('--symbol',action='append',required=True);a=p.parse_args();path=a.binary.resolve(strict=True);before=path.stat();raw=path.read_bytes();elf=ELFFile(BytesIO(raw));symtab=elf.get_section_by_name('.symtab');assert symtab is not None;assert elf.elfclass==64 and elf.little_endian,'Expected actual ELF64LSB host binary';assert elf['e_machine']=='EM_X86_64','Expected canonical x86_64 host';assert elf['e_type'] in ('ET_EXEC','ET_DYN');nm=subprocess.check_output(['nm','-a','--defined-only',str(path)],text=True);records={}
expected={'_ZL13raw_uu_encodePhjS_':'STT_FUNC','_ZL19curlRequestCallbackPvjjS_':'STT_FUNC','_ZN12_GLOBAL__N_117startMillisecondsE':'STT_OBJECT'}
assert len(a.symbol)==len(set(a.symbol)) and set(a.symbol)<=set(expected),'Finite approved symbol set only'
for name in a.symbol:
 rows=[s for s in symtab.get_symbol_by_name(name) or [] if s['st_shndx']!='SHN_UNDEF'];row,=rows;assert row['st_info']['bind']=='STB_LOCAL';assert row['st_info']['type']==expected[name] and row['st_size']>0;line,=[line for line in nm.splitlines() if line.split()[-1:]==[name]];assert int(line.split()[0],16)==row['st_value'];section=elf.get_section(row['st_shndx']);assert section['sh_flags']&2,'Allocated section required';relative=row['st_value']-section['sh_addr'];assert 0<=relative<=relative+row['st_size']<=section['sh_size'];required=2 if name=='_ZN12_GLOBAL__N_117startMillisecondsE' else 1
 if required==2:assert row['st_info']['type']=='STT_OBJECT' and row['st_size']==8 and section['sh_flags']&1
 else:assert row['st_info']['type']=='STT_FUNC' and row['st_size']>0 and section['sh_flags']&4 and section['sh_type']!='SHT_NOBITS'
 loads=[seg for seg in elf.iter_segments() if seg['p_type']=='PT_LOAD' and seg['p_flags']&required==required and seg['p_vaddr']<=row['st_value'] and row['st_value']+row['st_size']<=seg['p_vaddr']+seg['p_memsz']]
 assert len(loads)==1,'Exact symbol lacks required executable/writable PT_LOAD range'
 if required==1:
  segment=loads[0];delta=row['st_value']-segment['p_vaddr'];assert delta+row['st_size']<=segment['p_filesz'];assert segment['p_offset']+delta==section['sh_offset']+relative
 record={'required_PT_LOAD_flags':required,'PT_LOAD':{k:loads[0][k] for k in ('p_vaddr','p_memsz','p_filesz','p_offset','p_flags')},'mangled':name,'address':row['st_value'],'size':row['st_size'],'section':row['st_shndx'],'section_name':section.name,'nm_row':line,'kind':row['st_info']['type']}
 if section['sh_type']=='SHT_NOBITS':record['initialization']='SHT_NOBITS zero-initialized object; no file-backed byte extraction'
 else:
  offset=section['sh_offset']+relative;body=raw[offset:offset+row['st_size']];assert len(body)==row['st_size'];record.update(file_offset=offset,body_sha256=hashlib.sha256(body).hexdigest())
 records[name]=record
now=path.stat();assert (now.st_dev,now.st_ino,now.st_size,now.st_mtime_ns,now.st_ctime_ns)==(before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns) and path.read_bytes()==raw;proof={'binary':str(path),'sha256':hashlib.sha256(raw).hexdigest(),'provenance':{'device':before.st_dev,'inode':before.st_ino,'size':before.st_size,'mtime_ns':before.st_mtime_ns,'ctime_ns':before.st_ctime_ns},'elf_machine':'EM_X86_64','elf_class':64,'elf_little_endian':True,'elf_type':elf['e_type'],'symbols':records,'nm_sha256':hashlib.sha256(nm.encode()).hexdigest(),'scope':'Actual host symbol mapping only; runtime load bias must use same binary/DSO; no original ARM ABI or hardware proof.'};a.out.parent.mkdir(parents=True,exist_ok=True)
with a.out.open('x') as f:json.dump(proof,f,indent=2);f.write('\n')
