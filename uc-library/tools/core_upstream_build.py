#!/usr/bin/env python3
"""Try the unmodified upstream Core target with project-local build products."""
import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.partial')
    temporary.write_text(json.dumps(value,indent=2)+'\n');temporary.replace(path)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository',type=Path,required=True)
    parser.add_argument('--cmake',type=Path,required=True)
    parser.add_argument('--builtin-modules',type=Path,required=True)
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args()
    root=args.repository.resolve();cmake=args.cmake.resolve();source=root/'third_party/ccl-framework'
    build=args.build.resolve();evidence=args.evidence.resolve();evidence.mkdir(parents=True,exist_ok=True)
    scratch=root/'temp/core-upstream/tmp';scratch.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,TMPDIR=str(scratch),PIP_CACHE_DIR=str(root/'temp/core-upstream/pip-cache'))
    core_files={str(path.relative_to(source)):sha(path) for path in (source/'core').rglob('*') if path.is_file()}
    configure=[str(cmake),'-S',str(source/'core/cmake'),'-B',str(build),
        '-DCMAKE_MODULE_PATH='+str(args.builtin_modules.resolve())+';'+str(source/'build/cmake/modules/shared'),
        '-DCMAKE_PREFIX_PATH='+str(source/'core/cmake'),
        '-DCMAKE_INCLUDE_PATH='+str(root/'temp/core-upstream/external-dev/usr/include')+';'+str(root/'temp/core-upstream/external-dev/usr/include/avahi-compat-libdns_sd'),
        '-DCMAKE_CXX_FLAGS=-isystem '+str(root/'temp/core-upstream/external-dev/usr/include')+' -isystem '+str(root/'temp/core-upstream/external-dev/usr/include/libpng16'),
        '-DPNG_PNG_INCLUDE_DIR='+str(root/'temp/core-upstream/external-dev/usr/include/libpng16'),
        '-DPNG_LIBRARY=/usr/lib/x86_64-linux-gnu/libpng16.so.16',
        '-Ddnssd_INCLUDE_DIR='+str(root/'temp/core-upstream/external-dev/usr/include/avahi-compat-libdns_sd'),
        '-DVENDOR_OUTPUT_DIRECTORY='+str(root/'temp/core-upstream/build-output'),
        '-DVENDOR_USE_CACHE_DIRECTORY=OFF','-DVENDOR_ENABLE_PARALLEL_BUILDS=ON',
        '-DPROJECT_DEBUG_SUFFIX=','-Dcorelib_BUILD_TESTAPP=OFF','-DCMAKE_BUILD_TYPE=Release']
    commands=dict(configure=configure,build=[str(cmake),'--build',str(build),'--target','corelib','-j1'])
    atomic(evidence/'commands.json',commands)
    results={}
    for name,command in commands.items():
        print(json.dumps(dict(event='starting',phase=name)),flush=True)
        with (evidence/(name+'.log')).open('w') as log:
            result=subprocess.run(command,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT)
        results[name]=result.returncode
        print(json.dumps(dict(event='finished',phase=name,exit_code=result.returncode)),flush=True)
        if result.returncode:break
    after={str(path.relative_to(source)):sha(path) for path in (source/'core').rglob('*') if path.is_file()}
    unchanged=core_files==after
    report=dict(phases=results,core_source_files_unchanged=unchanged,
        framework_build_passed=results.get('configure')==0 and results.get('build')==0,
        original_behavior_verified=False,original_arm_abi_verified=False,
        added_core_paths=sorted(set(after)-set(core_files)),modified_core_paths=[name for name in core_files if after.get(name)!=core_files[name]],
        logs={path.name:sha(path) for path in evidence.glob('*.log')},tool_sha256=sha(Path(__file__)))
    atomic(evidence/'validation.json',report)
    print(json.dumps(report,indent=2))
    if not report['framework_build_passed'] or not unchanged:raise SystemExit(1)


if __name__=='__main__':main()
