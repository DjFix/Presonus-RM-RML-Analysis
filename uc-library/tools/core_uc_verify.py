#!/usr/bin/env python3
"""Compile/check the original namespaces/mangling and compare to ARM buffer fixtures."""
import argparse
import hashlib
import json
import shutil
import struct
import subprocess
from datetime import datetime,timezone
from pathlib import Path


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('repository',type=Path)
    p.add_argument('--compiler',default='g++')
    a=p.parse_args()
    repository=a.repository.resolve()
    library=repository/'uc-library'
    target=library/'validation/core-uc'
    oracle=json.loads((target/'oracle.json').read_text())
    vectors=target/'arm-vectors.bin'
    assert sha(vectors)==oracle['vectors_sha256'],'oracle fixture identity changed'
    with vectors.open('rb') as stream:
        header=stream.read(12)
    assert header[:8]==b'UCBFv001' and struct.unpack('<I',header[8:])[0]==oracle['records']
    assert vectors.stat().st_size==12+280*oracle['records'],'truncated vector file'
    for original in oracle['originals']:
        name='surface' if original['role']=='client' else 'mixer'
        version='CS18_v13840' if name=='surface' else 'RML16AI_Rack_13731'
        assert sha(repository/'rootfs'/version/'home/root'/name)==original['original_elf_sha256']
    run=target/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run.mkdir(parents=True)
    source='src/core_uc/buffer.cpp'
    header_source='include/presonus/core_uc/buffer.hpp'
    test_source='tests/core_uc_tests.cpp'
    formatting_path=library/'validation/formatting.json'
    formatting=json.loads(formatting_path.read_text())
    assert formatting['format_check_passed'], 'formatter gate was not passed'
    for name in (source,header_source,test_source):
        assert formatting['files'][name]==sha(library/name), 'formatted source changed: '+name
    formatting_reference=dict(path='validation/formatting.json',sha256=sha(formatting_path),
        formatter=formatting['formatter'],configuration_sha256=formatting['configuration_sha256'],
        format_check_passed=True,scoped_files={name:formatting['files'][name] for name in (source,header_source,test_source)})
    (run/'formatting.json').write_bytes(formatting_path.read_bytes())
    obj=run/'buffer.o'
    executable=run/'core_uc_tests'
    def command(arguments,name):
        result=subprocess.run(arguments,cwd=library,text=True,capture_output=True)
        (run/name).write_text('COMMAND: '+json.dumps(arguments)+'\n'+result.stdout+result.stderr)
        if result.returncode:
            print(result.stdout+result.stderr,flush=True)
            result.check_returncode()
        return result.stdout
    command([a.compiler,'-std=c++17','-O2','-Wall','-Wextra','-Wpedantic','-Iinclude','-c',source,'-o',str(obj)],'compile.log')
    command([a.compiler,'-std=c++17','-O2','-Wall','-Wextra','-Wpedantic','-Iinclude',test_source,str(obj),'-o',str(executable)],'test-build.log')
    test_output=command([str(executable),str(vectors)],'tests.log')
    assert f'PASS: {oracle["records"]} original-ARM fixtures' in test_output,'incomplete C++ comparison'
    names=command(['nm','--defined-only',str(obj)],'symbols.log')
    expected={s['mangled'] for entry in oracle['originals'] for s in entry['functions']}
    defined={line.split()[-1] for line in names.splitlines() if line.split()}
    assert expected<=defined, 'original mangled names not emitted: '+str(expected-defined)
    source_paths=(source,header_source,test_source,'tools/core_uc_oracle.py','tools/core_uc_verify.py')
    sources={path:sha(library/path) for path in source_paths}
    for name in (source,header_source,test_source):
        assert formatting['files'][name]==sources[name], 'source changed during validation: '+name
    evidence=repository/'evidence/recovery/2026-10-26/core-uc-format'/run.name
    proof=dict(namespace='Presonus::UC',classes=['BufferReader','BufferWriter'],
               originals=oracle['originals'],mangled_names=sorted(expected),
               compiled_mangled_names_matched=True,cpp_differential_passed=True,
               records=oracle['records'],cases=oracle['cases'],partial_mutation_failures=oracle['partial_mutation_failures'],
               domain=oracle['domain'],external_dependencies=oracle['external_dependencies'],
               declaration_uncertainties=oracle['declaration_uncertainties'],sources=sources,
               formatting_reference=formatting_reference,evidence_directory=str(evidence.relative_to(repository)),
               vectors_sha256=oracle['vectors_sha256'],object_sha256=sha(obj),test_binary_sha256=sha(executable),
               test_output=test_output,compiler=command([a.compiler,'--version'],'compiler.log').splitlines()[0],
               object_format=command(['file',str(obj)],'object-format.log').strip(),
               original_arm_object_layout_compatible=False,original_function_fully_verified=False,
               hardware_verified=False,run_directory=str(run.relative_to(library)),
               limits='Portable observed buffer semantics only; not exact original header declarations or libc recovery.')
    proof_path=target/'validation.json'
    proof_text=json.dumps(proof,indent=2)+'\n'
    (run/'validation.json').write_text(proof_text)
    proof_path.write_text(proof_text)
    ready=[]
    for original in oracle['originals']:
        for symbol in original['functions']:
            ready.append(dict(mangled=symbol['mangled'],original_elf_sha256=original['original_elf_sha256'],
                original_address=symbol['address'],validation='validation/core-uc/validation.json',
                validation_sha256=sha(proof_path),sources=sources,portable_ready=True,domain=oracle['domain'],
                original_return_declaration_proven='EEb' in symbol['mangled']))
    fragment={'functions':ready}
    text=json.dumps(fragment,indent=2)+'\n'
    (target/'ready-functions.fragment.json').write_text(text)
    (run/'ready-functions.fragment.json').write_text(text)
    evidence.mkdir(parents=True,exist_ok=False)
    for path in source_paths:
        destination=evidence/'source'/path
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(library/path,destination)
    for name in ('oracle.json','arm-vectors.bin','validation.json','ready-functions.fragment.json'):
        shutil.copyfile(target/name,evidence/name)
    shutil.copytree(run,evidence/'runs'/run.name)
    shutil.copyfile(formatting_path,evidence/'formatting.json')
    files=[path for path in sorted(evidence.rglob('*')) if path.is_file() and path.name!='SHA256SUMS']
    (evidence/'SHA256SUMS').write_text(''.join(sha(path)+'  '+str(path.relative_to(evidence))+'\n' for path in files))
    print(test_output,end='')
    print(f'PASS: {len(expected)} compiled original mangled names; {len(ready)} ELF-symbol readiness records; original namespaces retained.')
    print('Domain and declaration/layout limitations remain explicit; no hardware verification.')
    print('Fresh evidence directory: '+str(evidence.relative_to(repository)))


if __name__=='__main__':main()
