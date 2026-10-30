"""Seal original socket-channel methods with explicit external I/O and codec composition."""
import sys,json,struct,hashlib,subprocess,shutil,argparse,datetime,re
from pathlib import Path
from elftools.elf.elffile import ELFFile
from elftools.elf.relocation import RelocationSection
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
VTABLE='_ZTVN8Presonus2UC16SocketConnection7ChannelE'
PREFIX='_ZN8Presonus2UC16SocketConnection7Channel'
SLOTS=[PREFIX+x for x in ['10isReadableEi','17getBytesAvailableEv','4readEPvi','10isWritableEi','14getGranularityEv','5writeEPKvi','9hasErrorsEi','D1Ev','D0Ev']]
def inspect_vtables(repo,lib,obj,originals):
 result={'originals':[],'native':{},'original_destructor_semantics_recovered':False,'original_arm_abi_compatible':False}
 for original in originals:
  manifest=json.loads((lib/'recovered'/original['role']/'manifest.json').read_text())
  with (repo/manifest['path']).open('rb') as f:
   elf=ELFFile(f);symbols=list(elf.get_section_by_name('.symtab').iter_symbols());v=next(s for s in symbols if s.name==VTABLE)
   sec=elf.get_section(v['st_shndx']);off=v['st_value']-sec['sh_addr'];raw=sec.data()[off:off+v['st_size']]
   assert elf.elfclass==32 and len(raw)==44
   words=struct.unpack('<11I',raw);assert words[0]==0
   slots=[]
   for i,name in enumerate(SLOTS):
    s=next(s for s in symbols if s.name==name and s['st_value'])
    assert words[i+2]==s['st_value']
    slots.append(dict(index=i,byte_offset_from_address_point=4*i,mangled=name,address=words[i+2],bounded_portable_function_scope_ready=i<7))
   result['originals'].append(dict(role=original['role'],original_elf_sha256=original['original_elf_sha256'],mangled=VTABLE,address=v['st_value'],address_point=v['st_value']+8,size=len(raw),sha256=hashlib.sha256(raw).hexdigest(),slots=slots))
 with obj.open('rb') as f:
  elf=ELFFile(f);symbols=list(elf.get_section_by_name('.symtab').iter_symbols());v=next(s for s in symbols if s.name==VTABLE)
  pointer=elf.elfclass//8;assert pointer==8 and v['st_size']==11*pointer
  raw=elf.get_section(v['st_shndx']).data()[v['st_value']:v['st_value']+v['st_size']]
  assert int.from_bytes(raw[:pointer],'little')==0
  relocations={}
  for section in elf.iter_sections():
   if isinstance(section,RelocationSection) and section['sh_info']==v['st_shndx']:
    symtab=elf.get_section(section['sh_link'])
    for relocation in section.iter_relocations():
     offset=relocation['r_offset']-v['st_value']
     if 0<=offset<v['st_size']:relocations[offset]=symtab.get_symbol(relocation['r_info_sym']).name
  slots=[]
  for i,name in enumerate(SLOTS):
   assert relocations[pointer*(i+2)]==name,(i,relocations)
   slots.append(dict(index=i,byte_offset_from_address_point=pointer*i,mangled=name,bounded_portable_function_scope_ready=i<7,portable_lifetime_helper=i>=7))
  result['native']=dict(object_format='ELF64',pointer_bytes=pointer,vtable_size=v['st_size'],mangled=VTABLE,address_point_byte_offset=2*pointer,slots=slots)
 return result
def main():
 p=argparse.ArgumentParser();p.add_argument('repository',type=Path);p.add_argument('--formatter',type=Path,required=True);a=p.parse_args()
 repo=a.repository.resolve();lib=repo/'uc-library';target=lib/'validation/uc-socket-channel'
 oracle=json.loads((target/'oracle.json').read_text());vectors=target/'arm-vectors.bin'
 assert sha(vectors)==oracle['vectors_sha256'] and vectors.stat().st_size>=12+296*oracle['records']
 assert vectors.read_bytes()[:12]==b'UCCHv001'+struct.pack('<I',oracle['records'])
 for original in oracle['originals']:
  manifest=json.loads((lib/'recovered'/original['role']/'manifest.json').read_text());assert sha(repo/manifest['path'])==original['original_elf_sha256']
 run=target/'runs'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');run.mkdir(parents=True,exist_ok=False)
 def command(args,name):
  args=list(map(str,args));r=subprocess.run(args,cwd=lib,text=True,capture_output=True);(run/name).write_text('COMMAND: '+json.dumps(args)+'\n'+r.stdout+r.stderr)
  if r.returncode:print(r.stdout+r.stderr,flush=True)
  r.check_returncode();return r.stdout
 source='src/Presonus/UC/socket_channel.cpp';header='include/presonus/uc/socket_channel.hpp';test='tests/uc_socket_channel_tests.cpp';virtual_test='tests/uc_socket_channel_virtual_tests.cpp';scoped=[source,header,test,virtual_test]
 formatter=command([a.formatter,'--version'],'formatter.log').strip();assert '23.1.3' in formatter
 command([a.formatter,'--style=file:'+str(repo/'.clang-format'),'-i',*scoped],'format-apply.log')
 command([a.formatter,'--style=file:'+str(repo/'.clang-format'),'--dry-run','--Werror',*scoped],'format-check.log')
 formatting=dict(formatter=formatter,configuration_sha256=sha(repo/'.clang-format'),format_check_passed=True,files={x:sha(lib/x) for x in scoped})
 (run/'formatting.json').write_text(json.dumps(formatting,indent=2)+'\n')
 dependencies=['src/Presonus/UC/event_factory.cpp','src/core_uc/buffer.cpp','src/Presonus/UC/events.cpp','src/Presonus/UC/primitive_dispatch.cpp','src/Presonus/UC/transport_events.cpp','src/Presonus/UC/discovery_events.cpp'];closure=set(scoped+dependencies);pending=list(scoped+dependencies)
 while pending:
  file=lib/pending.pop()
  for inc in re.findall(r'^#include\s+"([^"]+)"',file.read_text(),re.M):
   name='include/'+inc;path=lib/name;assert path.is_file(),name
   if name not in closure:closure.add(name);pending.append(name)
 sources=sorted(closure|{'tools/core_uc_oracle.py','tools/uc_socket_channel_oracle.py','tools/uc_socket_channel_verify.py'})
 hashes={x:sha(lib/x) for x in sources};obj=run/'socket_channel.o';exe=run/'uc_socket_channel_tests'
 flags=['g++','-std=c++17','-O2','-Wall','-Wextra','-Wpedantic','-Iinclude']
 command([*flags,'-c',source,'-o',obj],'compile.log');command([*flags,test,*dependencies,obj,'-o',exe],'test-build.log')
 output=command([exe,vectors],'tests.log');assert f"{oracle['records']} original ARM SocketChannel fixtures passed" in output
 assert '12 composed factory/channel chunking/error/raw-bits groups passed' in output
 virtual_exe=run/'uc_socket_channel_virtual_tests'
 command([*flags,virtual_test,obj,'-o',virtual_exe],'virtual-test-build.log')
 virtual_output=command([virtual_exe],'virtual-tests.log')
 assert '7 source-native virtual overrides and portable virtual lifetime helper passed; original D1/D0 semantics unverified' in virtual_output
 vtables=inspect_vtables(repo,lib,obj,oracle['originals'])
 (run/'vtables.json').write_text(json.dumps(vtables,indent=2)+'\n')
 nm=command(['nm','--defined-only',obj],'symbols.log');defined={line.split()[-1] for line in nm.splitlines() if line.split()}
 expected={s['mangled'] for original in oracle['originals'] for s in original['functions']};assert expected<=defined,expected-defined
 assert hashes=={x:sha(lib/x) for x in sources}
 evidence=repo/'evidence/recovery/2026-10-26/uc-socket-channel'/run.name
 proof=dict(namespace='Presonus::UC',classes=['SocketConnection::Channel'],originals=oracle['originals'],sources=hashes,mangled_names=sorted(expected),compiled_mangled_names_matched=True,cpp_differential_passed=True,records=oracle['records'],cases=oracle['cases'],domain=oracle['domain'],external_dependencies=oracle['dependencies'],declaration_uncertainties=oracle['limitations'],formatting_reference=formatting,vectors_sha256=sha(vectors),object_sha256=sha(obj),test_binary_sha256=sha(exe),compiler=command(['g++','--version'],'compiler.log').splitlines()[0],test_output=output,original_arm_object_layout_compatible=False,original_function_fully_verified=False,hardware_verified=False,run_directory=str(run.relative_to(lib)),evidence_directory=str(evidence.relative_to(repo)))
 proof['fixture_format']='UCCHv001 LErecordcount;8LEu32inputs,resultLEu32,callcountLEu32,5LEu32percallback(method,arg1,arg2,flags,result),afterIO128bytes,sentPrefix128bytes. Callbackmethods0receive/1sendAll/2readable/3writable/4error/5available.'
 proof['virtualness']=vtables
 proof['native_virtual_test_output']=virtual_output
 proof['native_virtual_test_binary_sha256']=sha(virtual_exe)
 proof['declaration_uncertainties']=proof['declaration_uncertainties']+['Sevenmethodsvirtualness/orderprovenbybothELFvtables;nativevirtualdispatchchecked. Compiler-generateddefaultD1/D0areindependentPORTABLElifetimehelpers—notoriginaldestructorsemantics/notready. Nativevtablepointerwidth8vsoriginal4;nativevtable/layout/inheritance/RTTIARMABInotclaimed.']
 proofpath=target/'validation.json';proofpath.write_text(json.dumps(proof,indent=2)+'\n')
 ready=[]
 for original in oracle['originals']:
  for symbol in original['functions']:
   ready.append(dict(mangled=symbol['mangled'],original_elf_sha256=original['original_elf_sha256'],original_address=symbol['address'],validation='validation/uc-socket-channel/validation.json',validation_sha256=sha(proofpath),sources=hashes,portable_ready=True,domain=oracle['domain'],original_return_declaration_proven=False))
 (target/'ready-functions.fragment.json').write_text(json.dumps(dict(functions=ready),indent=2)+'\n')
 for name in ['validation.json','ready-functions.fragment.json']:shutil.copyfile(target/name,run/name)
 evidence.mkdir(parents=True,exist_ok=False)
 for name in sources:
  dest=evidence/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(lib/name,dest)
 for name in ['oracle.json','arm-vectors.bin','validation.json','ready-functions.fragment.json']:shutil.copyfile(target/name,evidence/name)
 shutil.copytree(run,evidence/'run');shutil.copyfile(repo/'temp/uc-socket-channel/oracle-01/log.txt',evidence/'oracle.log')
 for previous in sorted((target/'runs').iterdir()):
  if previous!=run and not (previous/'validation.json').exists():shutil.copytree(previous,evidence/'failed-replays'/previous.name)
 files=[x for x in sorted(evidence.rglob('*')) if x.is_file()];(evidence/'SHA256SUMS').write_text(''.join(sha(x)+'  '+str(x.relative_to(evidence))+'\n' for x in files))
 print(output,end='');print(virtual_output,end='');print('PASS:',len(expected),'mangles;',len(ready),'ELFentries;',evidence.relative_to(repo))
if __name__=='__main__':main()
