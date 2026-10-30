#!/usr/bin/env python3
"""Scoped formatting, compile/nm and original ARM fixture replay for UC parameter control codecs."""
import argparse
import hashlib
import json
import shutil
import struct
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('repository',type=Path)
    p.add_argument('--formatter',type=Path,required=True)
    p.add_argument('--compiler',default='g++')
    a=p.parse_args();repository=a.repository.resolve();library=repository/'uc-library'
    target=library/'validation/uc-parameter';oracle=json.loads((target/'oracle.json').read_text())
    vectors=target/'arm-vectors.bin'
    assert sha(vectors)==oracle['vectors_sha256']
    assert vectors.stat().st_size>=12+40*oracle['records']
    assert vectors.read_bytes()[:12]==b'UCPAv001'+struct.pack('<I',oracle['records'])
    for original in oracle['originals']:
        path=library/'recovered'/original['role']/'manifest.json'
        manifest=json.loads(path.read_text());assert sha(repository/manifest['path'])==original['elf_sha256']
    run=target/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');run.mkdir(parents=True)
    def command(args,name):
        r=subprocess.run([str(s) for s in args],cwd=library,text=True,capture_output=True)
        (run/name).write_text('COMMAND: '+json.dumps([str(s) for s in args])+'\n'+r.stdout+r.stderr)
        if r.returncode: print(r.stdout+r.stderr,flush=True)
        r.check_returncode();return r.stdout
    source='src/Presonus/UC/parameter_events.cpp';header='include/presonus/uc/parameter_events.hpp';test='tests/uc_parameter_tests.cpp'
    scoped=(source,header,test);config=repository/'.clang-format'
    formatter=command([a.formatter,'--version'],'formatter-version.log').strip()
    assert '23.1.3' in formatter
    command([a.formatter,'--style=file:'+str(config),'-i',*scoped],'format-apply.log')
    command([a.formatter,'--style=file:'+str(config),'--dry-run','--Werror',*scoped],'format-check.log')
    formatting=dict(formatter=formatter,configuration_sha256=sha(config),format_check_passed=True,
                    files={name:sha(library/name) for name in scoped})
    (run/'formatting.json').write_text(json.dumps(formatting,indent=2)+'\n')
    sources=(*scoped,'src/core_uc/buffer.cpp','include/presonus/core_uc/buffer.hpp',
             'src/Presonus/UC/event_factory.cpp','include/presonus/uc/event_factory.hpp',
             'src/Presonus/UC/events.cpp','include/presonus/uc/events.hpp',
             'include/presonus/uc/transport_events.hpp','include/presonus/uc/discovery_events.hpp',
             'include/presonus/uc/primitive_dispatch.hpp','include/presonus/uc/typed_factory_codec.hpp',
             'tools/uc_parameter_oracle.py','tools/uc_parameter_verify.py','tools/uc_meter_oracle.py','tools/core_uc_oracle.py','tools/uc_registration_map.py')
    hashes={name:sha(library/name) for name in sources}
    obj=run/'events.o';exe=run/'uc_parameter_tests'
    flags=[a.compiler,'-std=c++17','-O2','-Wall','-Wextra','-Wpedantic','-Iinclude']
    command([*flags,'-c',source,'-o',obj],'compile.log')
    command([*flags,test,'src/core_uc/buffer.cpp','src/Presonus/UC/events.cpp','src/Presonus/UC/event_factory.cpp',obj,'-o',exe],'test-build.log')
    output=command([exe,vectors],'tests.log')
    assert f'{oracle["records"]} original ARM parameter fixtures passed' in output
    nm=command(['nm','--defined-only',obj],'symbols.log')
    expected={s['mangled'] for original in oracle['originals'] for s in original['functions']}
    defined={line.split()[-1] for line in nm.splitlines() if line.split()}
    assert expected<=defined,expected-defined
    assert hashes=={name:sha(library/name) for name in sources},'sources changed during validation'
    evidence=repository/'evidence/recovery/2026-10-26/uc-parameter'/run.name
    proof=dict(namespace='Presonus::UC',classes=['ParamEditEventClass','ParamModeEventClass','ParamIncrementEventClass','ParamColorEventClass','ParamRangeEventClass','ParamStringListEventClass','PrimitiveEventClass'],
               originals=oracle['originals'],sources=hashes,mangled_names=sorted(expected),
               compiled_mangled_names_matched=True,cpp_differential_passed=True,
               records=oracle['records'],cases=oracle['cases'],partial_mutation_failures=oracle['partial_mutation_failures'],
               domain=oracle['domain'],external_dependencies=oracle['dependencies'],declaration_uncertainties=oracle['limitations'],
               formatting_reference=formatting,vectors_sha256=sha(vectors),object_sha256=sha(obj),test_binary_sha256=sha(exe),
               compiler=command([a.compiler,'--version'],'compiler.log').splitlines()[0],test_output=output,
               original_arm_object_layout_compatible=False,original_function_fully_verified=False,hardware_verified=False,
               run_directory=str(run.relative_to(library)),evidence_directory=str(evidence.relative_to(repository)))
    proofpath=target/'validation.json';proofpath.write_text(json.dumps(proof,indent=2)+'\n')
    ready=[]
    for original in oracle['originals']:
        for s in original['functions']:
            ready.append(dict(mangled=s['mangled'],original_elf_sha256=original['elf_sha256'],original_address=s['address'],
                              validation='validation/uc-parameter/validation.json',validation_sha256=sha(proofpath),sources=hashes,
                              portable_ready=True,domain=oracle['domain'],original_return_declaration_proven=False))
    (target/'ready-functions.fragment.json').write_text(json.dumps(dict(functions=ready),indent=2)+'\n')
    command([sys.executable,'tools/uc_registration_map.py',library],'registration-coverage.log')
    for name in ('validation.json','ready-functions.fragment.json'):shutil.copyfile(target/name,run/name)
    evidence.mkdir(parents=True)
    for name in sources:
        dest=evidence/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(library/name,dest)
    for name in ('oracle.json','arm-vectors.bin','validation.json','ready-functions.fragment.json'):shutil.copyfile(target/name,evidence/name)
    (evidence/'registration').mkdir()
    for name in ('coverage.json','COVERAGE.md'):
        shutil.copyfile(library/'validation/uc-registration'/name,evidence/'registration'/name)
    shutil.copytree(run,evidence/'runs'/run.name)
    for failed in sorted((target/'runs').iterdir()):
        if failed.is_dir() and (failed/'tests.log').exists() and not (failed/'validation.json').exists():
            shutil.copytree(failed,evidence/'failed-replays'/failed.name)
    files=[f for f in sorted(evidence.rglob('*')) if f.is_file()]
    (evidence/'SHA256SUMS').write_text(''.join(sha(f)+'  '+str(f.relative_to(evidence))+'\n' for f in files))
    print(output,end='');print('PASS:',len(expected),'original mangles;',len(ready),'ELF entries')
    print('Fresh evidence:',evidence.relative_to(repository))

if __name__=='__main__':main()
