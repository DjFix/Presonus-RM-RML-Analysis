#!/usr/bin/env python3
"""Compile scoped helper sources and record original-symbol/differential evidence."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repository',type=Path)
    parser.add_argument('--output',type=Path,required=True,
        help='New library-relative validation directory; must not already exist')
    args=parser.parse_args()
    library=args.repository/'uc-library'
    references=library/'validation/surface-panel'
    assert not args.output.is_absolute() and '..' not in args.output.parts
    evidence=library/args.output
    evidence.mkdir(parents=True,exist_ok=False)
    build=evidence/'build'
    build.mkdir()
    oracle=json.loads((references/'arm-oracle.json').read_text())
    assert digest(references/'arm-vectors.txt')==oracle['vectors_sha256'],'ARM fixture digest changed'
    formatting_path=library/'validation/formatting.json'
    formatting=json.loads(formatting_path.read_text())
    assert formatting['format_check_passed'] is True
    formatted_inputs=['src/surface_panel/ControlHelpers.cpp',
        'include/presonus/surface_panel/ControlHelpers.hpp','tests/surface_panel_tests.cpp']
    for name in formatted_inputs:
        assert digest(library/name)==formatting['files'][name],f'formatted source changed: {name}'
    assert digest(args.repository/'.clang-format')==formatting['configuration_sha256']
    log=[]
    def run(command):
        result=subprocess.run(command,cwd=library,check=True,capture_output=True,text=True)
        log.append('$ '+repr(command)+'\n'+result.stdout+result.stderr)
        return result.stdout
    source='src/surface_panel/ControlHelpers.cpp'
    relative_build=(args.output/'build').as_posix()
    run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Wpedantic','-Iinclude','-c',source,'-o',relative_build+'/ControlHelpers.o'])
    run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Wpedantic','-Iinclude','tests/surface_panel_tests.cpp',relative_build+'/ControlHelpers.o','-o',relative_build+'/surface_panel_tests'])
    result=run([relative_build+'/surface_panel_tests','validation/surface-panel/arm-vectors.txt'])
    expected_output=f'PASS: {oracle["counts"]["seven_segment"]} seven-segment, {oracle["counts"]["control_group"]} control-group, {oracle["counts"]["transport_name"]} transport-name ARM differential fixtures'
    assert expected_output in result,'test coverage differs from oracle case counts'
    names=run(['nm','--defined-only',relative_build+'/ControlHelpers.o'])
    defined={line.split()[-1] for line in names.splitlines() if line.split()}
    original_symbols=[dict(symbol,role=role,original_elf_sha256=record['sha256']) for role,record in oracle['originals'].items() for symbol in record['functions']]
    expected={symbol['mangled'] for symbol in original_symbols}
    assert expected<=defined, f'compiled mangled names missing: {expected-defined}'
    inputs=[source,'include/presonus/surface_panel/ControlHelpers.hpp','tests/surface_panel_tests.cpp','tools/surface_panel_oracle.py','tools/surface_panel_validate.py']
    sources={name:digest(library/name) for name in inputs}
    proof=dict(scope='surface-panel pure helpers',original_symbols=original_symbols,
        compiled_mangled_names_matched=True,compiled_mangled_names=sorted(expected),mangled_names=sorted(expected),
        cpp_differential_passed=True,portable_ready=True,counts=oracle['counts'],
        sources=sources,object_sha256=digest(build/'ControlHelpers.o'),
        executable_sha256=digest(build/'surface_panel_tests'),vectors_sha256=oracle['vectors_sha256'],
        oracle_metadata_sha256=digest(references/'arm-oracle.json'),
        oracle_metadata_reference='validation/surface-panel/arm-oracle.json',
        fixture_reference='validation/surface-panel/arm-vectors.txt',
        formatting=dict(reference='validation/formatting.json',
            sha256=digest(formatting_path),formatter=formatting['formatter'],
            configuration_reference='../.clang-format',
            format_check_passed=True,configuration_sha256=formatting['configuration_sha256'],
            verified_source_hashes={name:formatting['files'][name] for name in formatted_inputs}),
        test_output=result,domain=oracle['domain'],dependency_model=oracle['dependency_model'],
        declaration_uncertainties=oracle['declaration_uncertainties']+[
            'Original C++ return spelling of all methods remains unresolved: portable uint16_t/int/bool declarations match observed R0 values, not proven original headers.',
            'Original ControlType enumerator names/range/underlying declaration are unresolved; the portable nested enum has fixed int32 domain.',
        ],original_arm_object_layout_compatible=False,original_full_verification=False,hardware_verified=False)
    (evidence/'linux-validation.log').write_text(''.join(log))
    proof_path=evidence/'reconstruction.json'
    proof_path.write_text(json.dumps(proof,indent=2)+'\n')
    records=[]
    for symbol in original_symbols:
        records.append(dict(mangled=symbol['mangled'],original_elf_sha256=symbol['original_elf_sha256'],
            original_address=symbol['address'],validation=(args.output/'reconstruction.json').as_posix(),
            validation_sha256=digest(proof_path),sources=sources,portable_ready=True,
            domain=oracle['domain'],original_full_verification=False,hardware_verified=False,
            declaration_uncertainties=proof['declaration_uncertainties']))
    (evidence/'readiness-records.json').write_text(json.dumps({'functions':records},indent=2)+'\n')
    print(result,end='')
    print('PASS: 3 exact compiled mangled names; 4 original ELF/symbol entries validated for the stated portable domain.')


if __name__=='__main__':main()
