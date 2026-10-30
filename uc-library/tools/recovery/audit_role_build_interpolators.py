#!/usr/bin/env python3
"""Audit current source partitions, installed role archives and relocated consumers."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repository',type=Path)
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--prefix',type=Path,required=True)
    args=parser.parse_args()
    repo=args.repository.resolve();lib=repo/'uc-library'
    build=(repo/args.build).resolve();prefix=(repo/args.prefix).resolve()
    assert build.is_relative_to(repo/'temp') and prefix.is_relative_to(repo/'temp')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    work=repo/'temp/role-build-audit'/stamp;work.mkdir(parents=True)
    (work/'tmp').mkdir()
    env=dict(os.environ,TMPDIR=str(work/'tmp'),TMP=str(work/'tmp'),TEMP=str(work/'tmp'))
    commands=[]
    def run(name,argv):
        result=subprocess.run(list(map(str,argv)),cwd=repo,env=env,text=True,
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        (work/(name+'.log')).write_text('COMMAND '+repr(list(map(str,argv)))+'\n'+result.stdout)
        commands.append(dict(name=name,argv=list(map(str,argv)),returncode=result.returncode))
        (work/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        if result.returncode:raise RuntimeError(name+': '+result.stdout[-4000:])
        return result.stdout
    groups_path=lib/'cmake/ProductionSourceGroups.cmake'
    groups={}
    for group,body in re.findall(r'set\(PRESONUS_(common|cs18|rm)_SOURCES\s*\n(.*?)\n\)',groups_path.read_text(),re.S):
        names=body.split()
        assert names and all(name.startswith('src/') and name.endswith('.cpp') for name in names)
        assert len(names)==len(set(names))
        groups[group]=set(names)
    assert set(groups)=={'common','cs18','rm'}
    all_sources=set().union(*groups.values())
    assert sum(map(len,groups.values()))==len(all_sources),'overlapping production partitions'
    assert all_sources=={str(path.relative_to(lib)) for path in (lib/'src').rglob('*.cpp')},'unclassified production CPP'
    integration=json.loads((lib/'validation/integration.json').read_text())
    assert integration['platform']=='linux' and integration['ctest_passed']
    for name,digest in integration['files'].items():assert sha(lib/name)==digest,name
    assert sha(repo/integration['test_log'])==integration['test_log_sha256']
    snapshot={name:sha(lib/name) for name in all_sources|{'CMakeLists.txt','cmake/CommonObjects.cmake','cmake/ProductionSourceGroups.cmake'}}
    counts=Counter();actual_groups={key:set() for key in groups};flags_by_source={}
    for item in json.loads((build/'compile_commands.json').read_text()):
        flags=item.get('command',' '.join(item.get('arguments',[])))
        match=re.search(r'CMakeFiles/presonus_(common|cs18|rm)_objects\.dir',flags)
        if not match:continue
        source=str(Path(item['file']).resolve().relative_to(lib))
        counts[source]+=1;actual_groups[match[1]].add(source);flags_by_source[source]=flags
        assert ('-fno-rtti' in flags) == (source in {'src/Presonus/DICE/Dice3ManagerServices.cpp','src/portable/dice/CclManagerServices.cpp','src/mixer_dsp/Interpolators.cpp'})
        assert '-Ulinux' in flags and '-pthread' in flags
        assert '-DPRESONUS_HAS_UPSTREAM_CORE=1' in flags and '-DCORE_USE_OPENSSL=1' in flags
        if source.endswith(('mixer_dsp/Dsp.cpp','mixer_dsp/FilterControllers.cpp','surface_panel/DbTable.cpp','surface_panel/MeterControl.cpp')):
            assert '-fno-fast-math' in flags and '-ffp-contract=off' in flags
            if 'clang' in flags.split()[0]:assert '-ffp-model=strict' in flags
        if source.endswith(('surface_panel/DbTable.cpp','surface_panel/MeterControl.cpp')):assert '-fno-builtin-powf' in flags
        if source.endswith('DICE/Dice3Programmer.cpp'):assert '-fno-fast-math' in flags
    assert {'src/mixer_dsp/Interpolators.cpp','src/mixer_dsp/Logarithm.cpp'} <= groups['common']
    for name in ('src/mixer_dsp/Interpolators.cpp','src/mixer_dsp/Logarithm.cpp'):
        for option in ('-fno-lto','-fno-fast-math','-ffp-contract=off','-frounding-math','-fno-builtin'):
            assert option in flags_by_source[name], (name,option)
    assert set(counts)==all_sources and set(counts.values())=={1}
    assert actual_groups==groups
    sdk=build/'upstream-core/sdk'
    sdk_hashes={str(path.relative_to(sdk)):sha(path) for path in sdk.rglob('*') if path.is_file()}
    assert all(name in sdk_hashes for name in ('lib/libcorelib.a','lib/libpresonus_core_allocator.a'))
    for name,digest in sdk_hashes.items():assert sha(prefix/name)==digest,name
    pin=run('core-pin',['git','-C',repo/'third_party/ccl-framework','rev-parse','HEAD']).strip()
    assert pin=='e8cbdea4a4a20e15111f5a690798a259c0374b31'
    assert not run('core-clean',['git','-C',repo/'third_party/ccl-framework','status','--porcelain','--untracked-files=all']).strip()
    provider_headers={name:digest for name,digest in sdk_hashes.items() if name.startswith('include/')}
    for name,digest in provider_headers.items():assert sha(repo/'third_party/ccl-framework'/name.removeprefix('include/presonus-core-5/'))==digest,name
    app_headers={name:digest for name,digest in integration['files'].items() if name.startswith('include/presonus/')}
    installed={str(path.relative_to(prefix)):sha(path) for path in (prefix/'include').rglob('*') if path.is_file()}
    assert installed=={**app_headers,**provider_headers}
    ready=json.loads((lib/'validation/ready-functions.json').read_text())['functions']
    required={'presonus_uc':{row['mangled'] for row in ready}}
    for role,target in (('client','presonus_cs18_components'),('server','presonus_rm_components')):
        identity=json.loads((lib/'recovered-all'/role/'manifest.json').read_text())['sha256']
        required[target]={row['mangled'] for row in ready if row['original_elf_sha256']==identity}
    archives={}
    for target,names in required.items():
        path=prefix/'lib'/('lib'+target+'.a')
        output=run('nm-'+target,['nm','-g','--defined-only',path])
        actual={line.split()[-1] for line in output.splitlines() if len(line.split())>=3 and line.split()[-2] in ('T','W','V','D','B','R','S')}
        assert names<=actual,(target,sorted(names-actual))
        assert sha(path)==sha(build/path.name)
        archives[target]=dict(sha256=sha(path),required_original_mangles=sorted(names))
    relocated=work/'relocated-prefix';shutil.copytree(prefix,relocated)
    for path in (relocated/'lib/cmake').rglob('*.cmake'):
        text=path.read_text();assert str(repo) not in text and '/upstream-core/sdk' not in text,path
    exports=(relocated/'lib/cmake/presonus_uc/presonus_uc_targets.cmake').read_text()
    private_math='src/DSP/SinglePole.cpp' in groups['rm']
    assert private_math
    installed_link_interfaces={}
    for target in ('presonus::uc','presonus::cs18_components','presonus::rm_components'):
        assert 'add_library('+target+' STATIC IMPORTED)' in exports
        blocks=re.findall(r'set_target_properties\('+re.escape(target)+r' PROPERTIES\n(.*?)\n\)',exports,re.S)
        assert len(blocks)==1,target
        interfaces=re.findall(r'^\s*INTERFACE_LINK_LIBRARIES "([^"]*)"\s*$',blocks[0],re.M)
        expected=['PresonusCore::Provider']
        if private_math:expected.append('presonus::private_glibc29')
        assert len(interfaces)==1 and interfaces[0].split(';')==expected,(target,interfaces,expected)
        installed_link_interfaces[target]=expected
    private_math_archive_sha256=None
    if private_math:
        private_archive=prefix/'lib/libpresonus_private_glibc29.a'
        assert sha(private_archive)==sha(build/'private-glibc29-provider/libpresonus_private_glibc29.a')
        private_math_archive_sha256=sha(private_archive)
    dependencies=repo/'temp/core-upstream/external-dev/usr'
    cmake=lib/'.venv/bin/cmake'
    run('consumer-configure',[cmake,'-S',lib/'candidates/common-build/consumer','-B',work/'consumer-build',
        '-DCMAKE_BUILD_TYPE=Release','-Dpresonus_uc_DIR='+str(relocated/'lib/cmake/presonus_uc'),
        '-DCMAKE_PREFIX_PATH='+str(relocated)+';'+str(dependencies),
        '-DPNG_PNG_INCLUDE_DIR='+str(dependencies/'include/libpng16'),
        '-DPNG_LIBRARY_RELEASE=/usr/lib/x86_64-linux-gnu/libpng16.so.16',
        '-DZLIB_LIBRARY_RELEASE=/usr/lib/x86_64-linux-gnu/libz.so.1',
        '-DCoreDNSSD_LIBRARY='+str(dependencies/'lib/x86_64-linux-gnu/libdns_sd.so')])
    run('consumer-build',[cmake,'--build',work/'consumer-build','-j2'])
    run('consumer-tests',[lib/'.venv/bin/ctest','--test-dir',work/'consumer-build','--output-on-failure'])
    assert snapshot=={name:sha(lib/name) for name in snapshot}
    report=dict(passed=True,production_cpp_compiled_once=True,production_units=len(all_sources),
        groups={key:len(value) for key,value in groups.items()},compile_counts=dict(counts),
        required_mangles={key:len(value) for key,value in required.items()},archives=archives,
        application_headers=len(app_headers),provider_headers=len(provider_headers),
        provider_commit=pin,source_hashes=snapshot,sdk_hashes=sdk_hashes,
        integration_sha256=sha(lib/'validation/integration.json'),root_suites=integration['test_suites'],
        ready_ledger_sha256=sha(lib/'validation/ready-functions.json'),
        compile_commands_sha256=sha(build/'compile_commands.json'),
        relocated_role_consumers_passed=True,installed_link_interfaces=installed_link_interfaces,
        private_math_archive_sha256=private_math_archive_sha256,commands=commands,tool_sha256=sha(Path(__file__)),
        application_startup_complete=False,original_arm_abi_verified=False,hardware_verified=False)
    (work/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    destination=lib/'validation/role-build-audit/runs'/stamp;destination.mkdir(parents=True)
    for path in work.iterdir():
        if path.is_file():shutil.copyfile(path,destination/path.name)
    evidence=repo/'evidence/recovery/2026-10-27/role-build-audit'/stamp
    shutil.copytree(destination,evidence)
    (evidence/'manifest.json').write_text(json.dumps({path.name:sha(path) for path in evidence.iterdir() if path.is_file()},indent=2)+'\n')
    print(json.dumps(dict(passed=True,proof=str((destination/'validation.json').relative_to(lib)),
        sha256=sha(destination/'validation.json'),units=len(all_sources),groups=report['groups'],mangles=report['required_mangles'])))


if __name__=='__main__':main()
