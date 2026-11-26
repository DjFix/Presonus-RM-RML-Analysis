"""Test-only environment from strict postlink maps. Recheck before/after replay."""
import hashlib,json,pathlib
LPC={'_ZL13raw_uu_encodePhjS_':('PRESONUS_LPC_RAW','STT_FUNC'), '_ZN12_GLOBAL__N_117startMillisecondsE':('PRESONUS_LPC_START','STT_OBJECT')}
UPDATER={'_ZL19curlRequestCallbackPvjjS_':('PRESONUS_UPDATER_CALLBACK','STT_FUNC')}
def verified_environment(binary,map_path,kind):
 binary=pathlib.Path(binary).resolve(strict=True);m=json.loads(pathlib.Path(map_path).read_text());assert m['binary']==str(binary);data=binary.read_bytes();assert hashlib.sha256(data).hexdigest()==m['sha256'];st=binary.stat();assert m['provenance']==dict(device=st.st_dev,inode=st.st_ino,size=st.st_size,mtime_ns=st.st_mtime_ns,ctime_ns=st.st_ctime_ns);assert m['elf_class']==64 and m['elf_little_endian'] and m['elf_machine']=='EM_X86_64';expected=LPC if kind=='lpc' else UPDATER if kind=='updater' else None;assert expected is not None and set(m['symbols'])==set(expected);assert m['elf_type'] in (('ET_EXEC','ET_DYN') if kind=='lpc' else ('ET_DYN',));out={('PRESONUS_LPC_ELF_TYPE' if kind=='lpc' else 'PRESONUS_UPDATER_ELF_TYPE'):m['elf_type']}
 for name,(prefix,symbol_kind) in expected.items():
  record=m['symbols'][name];assert record['mangled']==name and record['kind']==symbol_kind and record['size']>0;required=2 if symbol_kind=='STT_OBJECT' else 1;seg=record['PT_LOAD'];assert record['required_PT_LOAD_flags']==required and seg['p_flags']&required==required;assert seg['p_vaddr']<=record['address'] and record['address']+record['size']<=seg['p_vaddr']+seg['p_memsz']
  if symbol_kind=='STT_OBJECT':assert record['size']==8
  else:assert record['address']+record['size']<=seg['p_vaddr']+seg['p_filesz']
  out[prefix+'_ADDR']=hex(record['address']);out[prefix+'_SIZE']=hex(record['size'])
 return out
