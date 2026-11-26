"""Finite strict GNU link-map provenance, canonical source/partition/member bytes.
No basename-only membership, unbound application archive, or ambiguous duplicate.
"""
import hashlib,json,pathlib,re,shlex

# Invocation-local snapshots only; module is loaded once by each finite runner.
_PRE={};_POST={};_PHASE='pre';_ARCHIVES={};_OBJECT_INDEX=None;_SYMBOLS={}
def _stream_sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def sha(p):
 p=pathlib.Path(p).resolve();cache=_PRE if _PHASE=='pre' else _POST
 if p not in cache:cache[p]=_stream_sha(p)
 return cache[p]
def bind(p):
 p=pathlib.Path(p).resolve();return {'path':str(p),'sha256':sha(p)}
def verify_snapshot():
 global _PHASE
 assert _PHASE=='pre'
 for p,h in list(_PRE.items()):
  current=_stream_sha(p);_POST[p]=current;assert current==h,('Input changed during invocation',p)
 _PHASE='post'
 return {'distinct_inputs':len(_PRE),'pre_hash_count':len(_PRE),'post_hash_count':len(_POST),'scope':'One streaming pre/post hash per distinct bound input; no persistent cache.'}
def ar_members(path):
 path=path.resolve();identity=(path,sha(path))
 if identity in _ARCHIVES:return _ARCHIVES[identity]
 names=b'';result=[];ordinal={}
 with path.open('rb') as f:
  assert f.read(8)==b'!<arch>\n',('regular GNU archive required',path)
  while True:
   h=f.read(60)
   if not h:break
   assert len(h)==60 and h[58:60]==b'`\n';size=int(h[48:58]);name=h[:16].decode().strip();remaining=size
   if name=='//':names=f.read(size);f.seek(size%2,1);continue
   if name in ('/','/SYM64/'):f.seek(size+size%2,1);continue
   if name.startswith('/') and name[1:].isdigit():name=names[int(name[1:]):].split(b'/\n',1)[0].decode()
   elif name.startswith('#1/'):
    n=int(name[3:]);name=f.read(n).decode();remaining-=n
   else:name=name.removesuffix('/')
   body_size=remaining;digest=hashlib.sha256()
   while remaining:
    chunk=f.read(min(1024*1024,remaining));assert chunk;digest.update(chunk);remaining-=len(chunk)
   f.seek(size%2,1);ordinal[name]=ordinal.get(name,0)+1;result.append({'member':name,'occurrence':ordinal[name],'sha256':digest.hexdigest(),'bytes':body_size})
 _ARCHIVES[identity]=result;return result

def live_map_text(raw):
 """GNU live-map evidence only; preamble/discarded sections never qualify."""
 lines=raw.splitlines();marker='Linker script and memory map'
 assert lines.count(marker)==1,('Exact single GNU live memory-map marker required',marker)
 return '\n'.join(lines[lines.index(marker)+1:])

def section_records(text):
 """Only one-line or exactly one continuation GNU input-section records.
 No search across a previous record, section heading, or arbitrary byte window.
 """
 result=[];pending=None
 owner=r'(?P<archive>[^\s()]+\.a)\((?P<member>[^()]+)\)'
 full=re.compile(r'^\s+(?P<section>\.[^\s]+)\s+0x[0-9a-fA-F]+\s+0x[0-9a-fA-F]+\s+'+owner+r'\s*$')
 continuation=re.compile(r'^\s+0x[0-9a-fA-F]+\s+0x[0-9a-fA-F]+\s+'+owner+r'\s*$')
 heading=re.compile(r'^\s+(?P<section>\.(?:text|rodata|data|bss)\.[^\s]+)\s*$')
 for number,line in enumerate(text.splitlines(),1):
  match=full.fullmatch(line)
  if match:result.append({**match.groupdict(),'line':number});pending=None;continue
  match=continuation.fullmatch(line)
  if match and pending is not None:result.append({**match.groupdict(),'section':pending['section'],'line':number-1});pending=None;continue
  # Pending state lasts exactly the immediately next physical line.
  match=heading.fullmatch(line);pending=match.groupdict() if match else None
 return result

def object_index(rows):
 global _OBJECT_INDEX
 if _OBJECT_INDEX is None:
  _OBJECT_INDEX={}
  for row in rows:
   output=pathlib.Path(row['output']);parts=output.parts
   if len(parts)<2 or parts[1] not in ('presonus_common_objects.dir','presonus_cs18_objects.dir','presonus_rm_objects.dir'):continue
   obj=pathlib.Path(row['directory'])/output
   if obj.is_file():_OBJECT_INDEX.setdefault(obj.name,[]).append((row,obj,parts[1]))
 return _OBJECT_INDEX

def prove_link(root,build,exe,driver,rows,contract,run,required_symbols,allowed_archives):
 key=str(exe.relative_to(root));entry=contract['targets'][key];mapfile=(root/entry['map']).resolve();assert mapfile.is_file() and sha(mapfile)==entry['sha256'];text=live_map_text(mapfile.read_text());row=driver['actual_compile_entry'];parts=pathlib.Path(row['output']).parts;linkfile=pathlib.Path(row['directory'])/parts[0]/parts[1]/'link.txt';cwd=pathlib.Path(row['directory']);tokens=shlex.split(linkfile.read_text());expanded=[]
 def expand(tokens):
  for token in tokens:
   if token.startswith('@'):
    p=pathlib.Path(token[1:]);p=p if p.is_absolute() else cwd/p;bound[str(p.resolve())]=bind(p.resolve());expand(shlex.split(p.read_text()))
   else:expanded.append(token)
 bound={};expand(tokens)
 allowed={p.resolve() for p in allowed_archives};driverobj=pathlib.Path(driver['object']['path']).resolve();actual_archives=set();direct=[]
 for token in expanded:
  if token.startswith('-'):continue
  p=pathlib.Path(token);p=(p if p.is_absolute() else cwd/p).resolve()
  if p.suffix in ('.a','.o') and p.is_file():
   bound[str(p)]=bind(p)
   if p.suffix=='.a':actual_archives.add(p)
   else:direct.append(p)
 # Resolve -l/system/linker-script transitives via actual GNU LOAD records.
 for match in re.finditer(r'^LOAD\s+(.+?)\s*$',text,re.M):
  name=match.group(1);p=pathlib.Path(name);p=(p if p.is_absolute() else cwd/p).resolve()
  if not p.is_file():continue
  bound[str(p)]=bind(p)
  if p.suffix=='.a':actual_archives.add(p)
  if p.suffix=='.o' and p not in direct:direct.append(p)
 assert driverobj in direct and (row['output'] in text or str(driverobj) in text),('actual driver map origin',driverobj)
 for obj in direct:
  assert obj==driverobj or str(obj).startswith(('/usr/lib/','/lib/')),('unbound/direct application body forbidden',obj)
 for archive in actual_archives:
  assert archive in allowed or str(archive).startswith(('/usr/lib/','/lib/')),('unbound/worker application archive forbidden',archive)
 facade=build/'libpresonus_uc.a';assert facade.resolve() in actual_archives,('canonical facade not actual linkinput',exe)
 actual_names={line.split()[-1] for line in run(['nm','--defined-only',exe]).splitlines() if len(line.split())>=3};assert required_symbols<=actual_names,('tested executable missing required identities',sorted(required_symbols-actual_names))
 member_records=[];archive_records=ar_members(facade);included=[];parsed_sections=section_records(text)
 for member in sorted({x['member'] for x in archive_records}):
  markers=[str(facade)+'('+member+')',facade.name+'('+member+')'];positions=[(marker,m.start()) for marker in markers for m in re.finditer(re.escape(marker),text)]
  if not positions:continue
  members=[x for x in archive_records if x['member']==member];candidates=[]
  for row2,obj,partition in object_index(rows).get(member,[]):
   h=sha(obj)
   for ar in members:
    if h==ar['sha256']:candidates.append({'archive':bind(facade),'member':ar,'source':bind(pathlib.Path(row2['file'])),'partition':partition,'canonical_object':bind(obj),'actual_compile_entry':row2})
  assert candidates,('included facade body lacks canonical source/object bytes',member)
  if len(members)==1:
   assert len(candidates)==1,('ambiguous canonical source for member bytes',member);chosen=candidates
  else:
   # A duplicate basename requires unique live input-section symbol evidence.
   found={};symbolsets={}
   for i,c in enumerate(candidates):
    path=c['canonical_object']['path']
    if path not in _SYMBOLS:_SYMBOLS[path]={line.split()[-1] for line in run(['nm','--defined-only',path]).splitlines() if len(line.split())>=3}
    symbolsets[i]=_SYMBOLS[path]
   exact_records=[]
   for record in parsed_sections:
    arpath=pathlib.Path(record['archive']);arpath=(arpath if arpath.is_absolute() else cwd/arpath).resolve()
    if arpath!=facade.resolve() or record['member']!=member:continue
    section=record['section'];symbol=next((section[len(prefix):] for prefix in ['.text.','.rodata.','.data.','.bss.'] if section.startswith(prefix)),None)
    if symbol is None:continue
    matches=[i for i,names in symbolsets.items() if symbol in names]
    if len(matches)==1:found[matches[0]]=symbol;exact_records.append(record)
   assert found,('duplicate basename map lacks unique symbol/source/occurrence evidence',member)
   chosen=[]
   for i,symbol in found.items():
    c=candidates[i];c['unique_map_section_symbol']=symbol;c['exact_same_input_section_records']=[x for x in exact_records if x['section'].endswith('.'+symbol)];assert c['exact_same_input_section_records'];chosen.append(c)
  for c in chosen:
   bound[c['source']['path']]=c['source'];bound[c['canonical_object']['path']]=c['canonical_object'];member_records.append(c)
  included.append(member)
 assert member_records,('no proven canonical application member origin',exe)
 return {'executable':bind(exe),'link_file':bind(linkfile),'map':bind(mapfile),'actual_link_tokens':expanded,'actual_archive_paths':sorted(map(str,actual_archives)),'bound_inputs':list(bound.values()),'canonical_facade_member_provenance':member_records,'required_symbols_verified_in_tested_exe':sorted(required_symbols),'standalone_symbol_union_is_executable_proof':False,'duplicate_basename_policy':'Only exact archive bytes/occurrence + source/partition/objectSHA with unique map-section symbol evidence; otherwise reject.'}
