#!/usr/bin/env python3
"""Compile unevaluated callable probes against real pinned Core declarations.

This tool never fabricates application class definitions. A failed probe is
recorded as unresolved, not as proof that an upstream callable does not exist.
"""
import argparse
import collections
import ctypes
import hashlib
import json
from pathlib import Path
from clang import cindex
from core_upstream_match import atomic, family, qualified, sha


def split_top(text,delimiter=','):
    result=[];start=0;angle=paren=bracket=0
    for index,char in enumerate(text):
        if char=='<':angle+=1
        elif char=='>':angle=max(angle-1,0)
        elif char=='(':paren+=1
        elif char==')':paren-=1
        elif char=='[':bracket+=1
        elif char==']':bracket-=1
        elif char==delimiter and not(angle or paren or bracket):result.append(text[start:index].strip());start=index+1
    result.append(text[start:].strip())
    return result


def callable_parts(text):
    end=text.rfind(')')
    if end<0:raise ValueError('No callable argument list')
    depth=1;start=end-1
    while start>=0:
        if text[start]==')':depth+=1
        elif text[start]=='(':
            depth-=1
            if not depth:break
        start-=1
    if start<0:raise ValueError('Unbalanced argument list')
    prefix=text[:start];positions=[];angle=0
    operator=prefix.find('::operator ')
    for index,char in enumerate(prefix):
        if char=='<':angle+=1
        elif char=='>':angle=max(angle-1,0)
        if not angle and prefix.startswith('Core::',index) and (operator<0 or index<operator):positions.append(index)
    if not positions:raise ValueError('No original Core callable scope')
    name=prefix[positions[-1]:]
    scopes=[];angle=0
    for index in range(len(name)-1):
        if name[index]=='<':angle+=1
        elif name[index]=='>':angle=max(angle-1,0)
        if not angle and name[index:index+2]=='::':scopes.append(index)
    if operator>=0:
        last=name.find('::operator')
    else:last=scopes[-1]
    owner,method=name[:last],name[last+2:]
    arguments=split_top(text[start+1:end]) if text[start+1:end].strip() else []
    return name,owner,method,arguments,text[end+1:].strip()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analysis',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--scratch',type=Path,required=True)
    parser.add_argument('--limit',type=int)
    args=parser.parse_args()
    analysis=args.analysis.resolve();out=args.output.resolve();scratch=args.scratch.resolve()
    out.mkdir(parents=True,exist_ok=True);scratch.mkdir(parents=True,exist_ok=True)
    config=json.loads((analysis/'configuration.json').read_text());source=Path(config['source'])
    cindex.Config.set_library_file(config['libclang']);index=cindex.Index.create()
    declarations=json.loads((analysis/'declarations.json').read_text())
    class_records=json.loads((analysis/'classes.json').read_text())
    classes={family(item['name']) for item in class_records}
    by_family=collections.defaultdict(list)
    for declaration in declarations:by_family[family(declaration['name'])].append(declaration)
    units=json.loads((analysis/'parse-units.json').read_text())
    headers=sorted(item['path'] for item in units if item['success'] and item['path'].endswith(('.h','.hpp')) and '/platform/' not in item['path'] and not item['path'].endswith(('coredefpush.h','coredefpop.h')))
    umbrella=scratch/'all-core.hpp'
    umbrella.write_text('#pragma once\n#include "core/public/coreplatform.h"\n#include "core/public/corevector.h"\n'+''.join('#include "'+name+'"\n' for name in headers))
    flags=list(config['flags'])+['-fno-access-control','-I'+str(scratch)]
    preamble='#include "all-core.hpp"\ntemplate<class T> T&& __core_upstream_declval() noexcept;\n'
    filename=str(scratch/'probe.cpp')
    tu=index.parse(filename,args=flags,unsaved_files=[(filename,preamble)],options=cindex.TranslationUnit.PARSE_PRECOMPILED_PREAMBLE)
    diagnostics=[str(item) for item in tu.diagnostics if item.severity>=cindex.Diagnostic.Error]
    atomic(out/'umbrella.json',dict(headers=headers,flags=flags,diagnostics=diagnostics,umbrella_sha256=sha(umbrella)))
    if diagnostics:
        print(json.dumps(dict(umbrella_success=False,diagnostics=diagnostics[:20]),indent=2));raise SystemExit(1)
    class RawString(ctypes.Structure):_fields_=[('data',ctypes.c_void_p),('flags',ctypes.c_uint)]
    class RawSet(ctypes.Structure):_fields_=[('strings',ctypes.POINTER(RawString)),('count',ctypes.c_uint)]
    native=ctypes.CDLL(config['libclang'])
    get_set=native.clang_Cursor_getCXXManglings;get_set.argtypes=[cindex.Cursor];get_set.restype=ctypes.POINTER(RawSet)
    get_string=native.clang_getCString;get_string.argtypes=[RawString];get_string.restype=ctypes.c_char_p
    dispose=native.clang_disposeStringSet;dispose.argtypes=[ctypes.POINTER(RawSet)]
    originals={}
    for role in ('client','server'):
        for item in json.loads((analysis/(role+'-functions.json')).read_text())['functions']:
            if not item['exact_encoded_interface_match']:originals.setdefault(item['mangled'],item)
    if args.limit:originals=dict(list(originals.items())[:args.limit])
    records=[];generated={}
    for number,(mangled,item) in enumerate(originals.items(),1):
        record=dict(mangled=mangled,demangled=item['demangled'],status='unresolved')
        if mangled.startswith(('_ZTh','_ZTv','_ZTc','_ZZ')):
            record['reason']='Compiler thunk/local identity requires separate implementation-level mapping';records.append(record);continue
        try:
            name,owner,method,arguments,suffix=callable_parts(item['demangled'])
            if any(token in ' '.join([owner,*arguments]) for token in ('Presonus::','DefaultMeterInterpolator','(anonymous namespace)')):
                record['reason']='Requires application/anonymous type definitions; none invented';records.append(record);continue
            values=','.join('__core_upstream_declval<'+argument+'>()' for argument in arguments)
            if family(owner) in classes:
                leaf=family(owner).split('::')[-1]
                if method.startswith('~'):
                    expression='__core_upstream_declval<__core_upstream_class&>().~__core_upstream_class()'
                elif family(method)==leaf:expression=owner+'('+values+')'
                elif any(value.get('static') for value in by_family[family(name)]):expression=owner+'::'+method+'('+values+')'
                else:
                    qualifiers=(' const' if 'const' in suffix else '')+(' volatile' if 'volatile' in suffix else '')
                    reference='&&' if '&&' in suffix else '&'
                    expression='__core_upstream_declval<'+owner+qualifiers+reference+'>().'+method+'('+values+')'
                alias='using __core_upstream_class='+owner+';\n'
            else:
                expression=name+'('+values+')';alias=''
            code=preamble+alias+'using __core_upstream_result=decltype('+expression+');\n'
            record['probe']=code
            code_key=hashlib.sha256((sha(umbrella)+json.dumps(flags)+sha(Path(__file__))+code).encode()).hexdigest();cache_file=scratch/(code_key+'.json')
            if cache_file.exists():result=json.loads(cache_file.read_text())
            else:
                tu.reparse(unsaved_files=[(filename,code)])
                errors=[str(value) for value in tu.diagnostics if value.severity>=cindex.Diagnostic.Error]
                referenced=[]
                if not errors:
                    for top in tu.cursor.get_children():
                        if top.spelling!='__core_upstream_result':continue
                        for child in top.walk_preorder():
                            target=child.referenced
                            if target is None or target.kind not in (cindex.CursorKind.CXX_METHOD,cindex.CursorKind.CONSTRUCTOR,cindex.CursorKind.DESTRUCTOR,cindex.CursorKind.FUNCTION_DECL,cindex.CursorKind.CONVERSION_FUNCTION):continue
                            if target.location.file is None:continue
                            path=Path(target.location.file.name).resolve()
                            if not path.is_relative_to(source/'core'):continue
                            names=[target.mangled_name] if target.mangled_name else []
                            if target.kind in (cindex.CursorKind.CONSTRUCTOR,cindex.CursorKind.DESTRUCTOR):
                                found=get_set(target)
                                if found:
                                    try:names += [get_string(found.contents.strings[i]).decode() for i in range(found.contents.count)]
                                    finally:dispose(found)
                            value=dict(name=qualified(target),path=str(path.relative_to(source)),line=target.location.line,usr=target.get_usr(),
                                type=target.type.spelling,result_type=target.result_type.spelling,arguments=[argument.type.spelling for argument in target.get_arguments()],mangled_names=sorted(set(names)))
                            value['generic_definitions']=[decl for decl in by_family[family(value['name'])] if decl['definition']]
                            referenced.append(value)
                result=dict(success=not errors,diagnostics=errors,referenced=referenced)
                atomic(cache_file,result)
            record.update(result)
            record['exact_match']=any(mangled in value['mangled_names'] for value in result['referenced'])
            record['status']='exact compiled callable reference' if record['exact_match'] else ('call compatible but different mangling' if result['success'] else 'unresolved')
            for value in result['referenced']:
                for actual in value['mangled_names']:generated.setdefault(actual,[]).append(value)
        except Exception as error:record['reason']=repr(error)
        records.append(record)
        if number%25==0:print(f'Probed {number}/{len(originals)}; exact {sum(value.get("exact_match",False) for value in records)}',flush=True)
    atomic(out/'probes.json',records);atomic(out/'generated-mangles.json',generated)
    summary=dict(commit=config['commit'],original_candidates=len(originals),attempted=sum('probe' in item for item in records),
        syntax_successes=sum(item.get('success',False) for item in records),exact_requested_matches=sum(item.get('exact_match',False) for item in records),
        generated_mangled_names=len(generated),status_counts=dict(collections.Counter(item['status'] for item in records)),
        invented_core_or_application_definitions=False,analysis_only=True)
    atomic(out/'summary.json',summary);print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
