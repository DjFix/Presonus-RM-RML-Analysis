#!/usr/bin/env python3
"""Compare original Core ELF names with compiler-mangled pinned upstream APIs.

No Core/application declarations are invented. Linux ARM system declarations
come from a separately hash-recorded cross sysroot. Parsing is not a framework
build, execution test, original layout proof, or return-type recovery.
"""
import argparse
import collections
import ctypes
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from clang import cindex
from elftools.elf.elffile import ELFFile
from extraction_verify_bounded import owning_namespace


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.partial')
    temporary.write_text(json.dumps(value,indent=2)+'\n');temporary.replace(path)


def family(text):
    output=[];depth=0
    for char in text:
        if char=='<':depth+=1
        elif char=='>':depth=max(depth-1,0)
        elif not depth:output.append(char)
    return ''.join(output)


def qualified(cursor):
    names=[]
    while cursor is not None and cursor.kind!=cindex.CursorKind.TRANSLATION_UNIT:
        if cursor.spelling:names.append(cursor.spelling)
        cursor=cursor.semantic_parent
    return '::'.join(reversed(names))


def run(args):
    source=args.source.resolve();library=args.library.resolve();output=args.output.resolve()
    output.mkdir(parents=True,exist_ok=True)
    commit=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    assert commit==args.commit,'selected source commit changed'
    assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain','--untracked-files=no'],text=True).strip(),'upstream source modified'
    tree=subprocess.check_output(['git','-C',str(source),'ls-tree','-r',commit,'core'],text=True)
    files=[]
    for line in tree.splitlines():
        metadata,name=line.split('\t',1);mode,kind,oid=metadata.split()
        if kind!='blob':continue
        path=source/name;data=path.read_bytes()
        assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==oid,name
        files.append(dict(path=name,git_blob_sha1=oid,sha256=sha(path),size=len(data)))
    atomic(output/'source-files.json',dict(commit=commit,files=files))
    cindex.Config.set_library_file(str(args.libclang.resolve()))
    index=cindex.Index.create()
    sysroot=args.sysroot.resolve()
    flags=['-x','c++','-std=c++17','-target','armv5te-unknown-linux-gnueabi','--sysroot='+str(sysroot),
           '-I'+str(source),'-isystem',str(sysroot/'include/c++/13'),'-isystem',str(sysroot/'include/c++/13/arm-linux-gnueabi'),
           '-ferror-limit=0','-Wno-pragma-once-outside-header','-Wno-inconsistent-missing-override']
    for path in args.external_include:flags+=['-isystem',str(path.resolve())]
    if args.generated_include:flags+=['-I'+str(path.resolve()) for path in args.generated_include]
    flags+=['-DCORE_BUILD_PATH="build"']
    packages_directory=sysroot.parents[2]/'sysroot-packages'
    packages={path.name:sha(path) for path in sorted(packages_directory.glob('*.deb'))}
    generated={str(path.resolve()):sha(path) for directory in args.generated_include for path in sorted(directory.rglob('*')) if path.is_file()}
    atomic(output/'configuration.json',dict(commit=commit,source=str(source),sysroot=str(sysroot),libclang=str(args.libclang.resolve()),flags=flags,
        parser_only=True,skip_function_bodies=not args.parse_bodies,original_arm_abi_verified=False,hardware_verified=False,
        tool_sha256=sha(Path(__file__)),libclang_sha256=sha(args.libclang.resolve()),system_packages=packages,generated_metadata=generated,
        python=sys.version,created_utc=datetime.now(timezone.utc).isoformat()))
    # Use raw CXString structures, so the set owns/disposes its strings exactly once.
    class RawString(ctypes.Structure):_fields_=[('data',ctypes.c_void_p),('flags',ctypes.c_uint)]
    class RawSet(ctypes.Structure):_fields_=[('strings',ctypes.POINTER(RawString)),('count',ctypes.c_uint)]
    native=ctypes.CDLL(str(args.libclang.resolve()))
    get_set=native.clang_Cursor_getCXXManglings;get_set.argtypes=[cindex.Cursor];get_set.restype=ctypes.POINTER(RawSet)
    get_string=native.clang_getCString;get_string.argtypes=[RawString];get_string.restype=ctypes.c_char_p
    dispose=native.clang_disposeStringSet;dispose.argtypes=[ctypes.POINTER(RawSet)];dispose.restype=None
    declarations={};classes={};units=[]
    relevant={cindex.CursorKind.CXX_METHOD,cindex.CursorKind.FUNCTION_DECL,cindex.CursorKind.CONSTRUCTOR,cindex.CursorKind.DESTRUCTOR,cindex.CursorKind.CONVERSION_FUNCTION,cindex.CursorKind.FUNCTION_TEMPLATE}
    class_kinds={cindex.CursorKind.CLASS_DECL,cindex.CursorKind.STRUCT_DECL,cindex.CursorKind.CLASS_TEMPLATE,cindex.CursorKind.CLASS_TEMPLATE_PARTIAL_SPECIALIZATION}
    def extract(tu):
        found=[];found_classes=[]
        def visit(cursor):
            for child in cursor.get_children():
                location=child.location
                if location.file is None:continue
                path=Path(location.file.name).resolve()
                if not path.is_relative_to(source/'core'):continue
                name=qualified(child)
                if name.startswith('Core::') and child.kind in class_kinds:
                    found_classes.append(dict(name=name,path=str(path.relative_to(source)),line=location.line,kind=child.kind.name))
                if name.startswith('Core::') and child.kind in relevant:
                    mangles=[]
                    if child.kind!=cindex.CursorKind.FUNCTION_TEMPLATE:
                        primary=child.mangled_name
                        if primary:mangles.append(primary)
                        if child.kind in (cindex.CursorKind.CONSTRUCTOR,cindex.CursorKind.DESTRUCTOR):
                            values=get_set(child)
                            if values:
                                try:mangles += [get_string(values.contents.strings[i]).decode() for i in range(values.contents.count)]
                                finally:dispose(values)
                    item=dict(name=name,displayname=child.displayname,kind=child.kind.name,
                              path=str(path.relative_to(source)),line=location.line,column=location.column,
                              usr=child.get_usr(),type=child.type.spelling,result_type=child.result_type.spelling,
                              arguments=[argument.type.spelling for argument in child.get_arguments()],
                              mangled_names=sorted(set(mangles)),definition=child.is_definition())
                    if item['definition']:
                        extent=child.extent
                        if extent.start.file and extent.end.file and extent.start.file.name==extent.end.file.name:
                            data=Path(extent.start.file.name).read_bytes()[extent.start.offset:extent.end.offset]
                            item.update(definition_extent_start=extent.start.offset,definition_extent_end=extent.end.offset,
                                        definition_extent_sha256=hashlib.sha256(data).hexdigest())
                    if child.kind==cindex.CursorKind.CXX_METHOD:
                        item.update(const=child.is_const_method(),static=child.is_static_method(),virtual=child.is_virtual_method())
                    found.append(item)
                visit(child)
        visit(tu.cursor)
        return found,found_classes
    candidates=[item for item in files if Path(item['path']).suffix in ('.h','.hpp','.inc','.cpp')]
    if args.limit:candidates=candidates[:args.limit]
    cache=args.cache.resolve();cache.mkdir(parents=True,exist_ok=True)
    base_key=hashlib.sha256(json.dumps(dict(commit=commit,flags=flags,tool=sha(Path(__file__)),parse_bodies=args.parse_bodies,packages=packages,generated=generated),sort_keys=True).encode()).hexdigest()
    for number,item in enumerate(candidates,1):
        name=item['path'];cache_file=cache/(hashlib.sha256((base_key+name).encode()).hexdigest()+'.json')
        if cache_file.exists():record=json.loads(cache_file.read_text())
        else:
            text='#include "'+name+'"\n' if not name.endswith('.cpp') else None
            if name=='core/public/coremap.h':text='#include "core/public/corevector.h"\n'+text
            if name=='core/public/coremalloc.h':text='#include "core/public/coreplatform.h"\n'+text
            path=str(cache/'parse.cpp') if text is not None else str(source/name)
            try:
                tu=index.parse(path,args=flags,unsaved_files=[(path,text)] if text is not None else [],options=0 if args.parse_bodies else cindex.TranslationUnit.PARSE_SKIP_FUNCTION_BODIES)
                diagnostics=[dict(severity=d.severity,message=str(d)) for d in tu.diagnostics]
                success=not any(d['severity']>=cindex.Diagnostic.Error for d in diagnostics)
                decls,records=extract(tu) if success else ([],[])
                record=dict(path=name,success=success,diagnostics=diagnostics,declarations=decls,classes=records)
                del tu
            except Exception as error:record=dict(path=name,success=False,diagnostics=[dict(message=repr(error))],declarations=[],classes=[])
            atomic(cache_file,record)
        units.append({key:value for key,value in record.items() if key not in ('declarations','classes')})
        for declaration in record['declarations']:
            key=(declaration['path'],declaration['line'],declaration['usr'],declaration['name'],tuple(declaration['mangled_names']))
            declarations[key]=declaration
        for value in record['classes']:classes[(value['name'],value['path'],value['line'])]=value
        if number%20==0:print(f'Parsed {number}/{len(candidates)} units; {sum(unit["success"] for unit in units)} successful',flush=True)
    values=list(declarations.values());class_values=list(classes.values())
    atomic(output/'parse-units.json',units);atomic(output/'declarations.json',values);atomic(output/'classes.json',class_values)
    by_mangle=collections.defaultdict(list)
    for item in values:
        for name in item['mangled_names']:by_mangle[name].append(item)
    class_families={family(item['name']) for item in class_values}
    callable_families={family(item['name']) for item in values}
    roles={}
    for role,filename,expected in (
        ('client','surface-13840.elf','304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'),
        ('server','mixer-13731.elf','9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07')):
        binary=args.inputs/filename;assert sha(binary)==expected
        with binary.open('rb') as stream:
            elf=ELFFile(stream);symtab=elf.get_section_by_name('.symtab')
            actual={(sym.name,int(sym['st_value']),int(sym['st_size']),sym['st_shndx']) for sym in symtab.iter_symbols() if sym['st_info']['type']=='STT_FUNC'}
        catalogue=json.loads((library/'recovered'/role/'all-symbols.json').read_text())
        symbols=[item for item in catalogue if item['kind']=='STT_FUNC' and isinstance(item['section'],int) and item['size'] and owning_namespace(item['mangled'])=='Core']
        assert len({item['mangled'] for item in symbols})==len(symbols)
        entries=[]
        for item in symbols:
            assert (item['mangled'],item['address'],item['size'],item['section']) in actual,'ELF catalogue mismatch'
            matches=by_mangle.get(item['mangled'],[])
            record=dict(item,original_elf_sha256=expected,upstream_commit=commit,exact_encoded_interface_match=bool(matches),
                        original_return_type_recovered=False,original_layout_verified=False,original_behavior_verified=False)
            if matches:
                record.update(status='upstream-source-provided; binary behavior unverified',skip_manual_reconstruction=True,
                    upstream=[dict(value,url=f'https://github.com/cclsoftware/ccl-framework/blob/{commit}/{value["path"]}#L{value["line"]}',source_sha256=sha(source/value['path'])) for value in matches],
                    source_body_available=any(value['definition'] for value in matches))
            else:
                text=item['demangled']
                if '<' in text and ('Presonus::' in text or 'DefaultMeterInterpolator' in text):category='templates involving application types'
                elif item['mangled'].startswith(('_ZTh','_ZTv','_ZTc')):category='compiler thunks'
                elif item['mangled'].startswith('_ZZ'):category='function-local symbols'
                elif re.search(r'D[012]E',item['mangled']):category='destructor ABI variants'
                elif '<' in text:category='other template instances'
                else:
                    prefix=text.split('(',1)[0]
                    category='unmatched callable or renamed/changed API'
                    if not any(name in prefix for name in class_families):category='scope without exact class family'
                record.update(status='source-port adaptation or application-specific analysis pending',category=category,skip_manual_reconstruction=False)
            entries.append(record)
        roles[role]=dict(original_elf_sha256=expected,total=len(entries),exact_matches=sum(item['exact_encoded_interface_match'] for item in entries),
                         source_body_available=sum(item.get('source_body_available',False) for item in entries),
                         remaining_categories=dict(collections.Counter(item['category'] for item in entries if not item['exact_encoded_interface_match'])),functions=entries)
        atomic(output/(role+'-functions.json'),roles[role])
    summary=dict(commit=commit,files=len(files),units_considered=len(units),units_successful=sum(item['success'] for item in units),
                 declarations=len(values),classes=len(class_values),mangled_names=len(by_mangle),
                 roles={role:{key:value for key,value in result.items() if key!='functions'} for role,result in roles.items()},
                 binary_behavior_verified=False,original_arm_abi_verified=False)
    atomic(output/'summary.json',summary)
    print(json.dumps(summary,indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--commit',default='e8cbdea4a4a20e15111f5a690798a259c0374b31')
    parser.add_argument('--library',type=Path,required=True)
    parser.add_argument('--inputs',type=Path,required=True)
    parser.add_argument('--sysroot',type=Path,required=True)
    parser.add_argument('--libclang',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--cache',type=Path,required=True)
    parser.add_argument('--external-include',type=Path,action='append',default=[])
    parser.add_argument('--generated-include',type=Path,action='append',default=[])
    parser.add_argument('--limit',type=int)
    parser.add_argument('--parse-bodies',action='store_true')
    run(parser.parse_args())


if __name__=='__main__':main()
