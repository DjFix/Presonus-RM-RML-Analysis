#!/usr/bin/env python3
"""Guarded LED + FileServer + partial raw-control application; NEVER runs validation/admission.

Default is plan-only. Root must inspect and invoke --apply explicitly.
Phase: led-server-control-root. No frozen producer is modified.

Dependency order after apply:
  1. Full strict formatting, fresh Linux114CTest/build/install/role95CPP/80headers.
  2. Fresh NOAA1ready+4pending, LED8ready+24pending, FileServer8pending components.
     Phase-specific NOAA/LED derivatives retain all native/range/symbol/source
     gates but label standalone tally requires_combined_preflight (not passed).
  3. Existing FileServer --finalize + --extra-ready/--extra-pending, or the
     unchanged root merger, checks ALL fresh LED+NOAA+FileServer fragments in
     ONE --dry-run before any admission:603ready/322names/320pending, stale0.
  4. Verify unchanged ledgers/history and all old identities, then root alone
     admits. Raw MCU has no host-ELF rows; separate bounded tracker/proof only.
No schema redesign, old-proof substitution, Core binary body or device IO.
"""
import argparse
import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil

BASELINE = {
    'CMakeLists.txt':'ae20c974e4e7d37a7897c93b1c56b72a04001bda44cc39e5899b49bbe5b09bdd',
    'cmake/ProductionSourceGroups.cmake':'efac447fe86d503e54d3b37e20a2f19a992d798c924519fac15675483dcfe670',
}
FIXTURES = [
 ('candidates/uc-file-server-service/validation/native-02/fixtures.stdin','validation/uc-file-server-service/fixtures.stdin','c446a9ccdf509225728b1da82f148c4dfd204d9ab30250d2d10b3f68c9f1c1db'),
 ('candidates/uc-file-server-service/validation/native-02/arm-output.txt','validation/uc-file-server-service/arm-output.txt','34c48c263f16321c3a4b6c31ce82d6fcaaca256f38e35d93b17eb19b9dd09a45'),
 ('candidates/efm-fader-control-dispatch/validation/native-01/fixtures.bin.gz','validation/embedded-efm/control/fixtures.bin.gz','ce63cb4bb69990e44a3a4fbe4e77c24356487617c052debb3ccada1df6dc172c'),
 ('candidates/efm-fader-control-dispatch/validation/native-01/arm-output.bin.gz','validation/embedded-efm/control/arm-output.bin.gz','a3c4e7113eb0dc8be16efa0284e5f22827bf5a4ee8bba1afe25a62f9bd167459'),
 ('candidates/panel-led-control-lifecycle/validation/new-01-arm/fixtures.jsonl','validation/panel-led-control-lifecycle/retained/fixtures.jsonl','f861ff0f92d9d8f9fd5f9ca2af87fc58ed4f1dc3949f28c45bdb6839aae0cd85'),
 ('candidates/panel-led-control-lifecycle/validation/new-01-arm/validation.json','validation/panel-led-control-lifecycle/retained/validation.json','dc20eeae239e354629723a361f151e0472f13a8f0c82753fe599a3f317c67a7e'),
 ('candidates/panel-led-control-lifecycle/validation/new-04/getter-normalization.json','validation/panel-led-control-lifecycle/retained/getter-normalization.json','ef311447e29e8503ec90fa4654d7a9d46d81dd0d2c530bc5878e8532c697828b'),
]
CONTROL_REPLAY = '''"""Lossless retained control records; no oracle or hardware execution."""
import argparse,gzip,hashlib,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--executable',required=True,type=Path)
p.add_argument('--fixtures',required=True,type=Path)
p.add_argument('--expected',required=True,type=Path)
a=p.parse_args()
assert hashlib.sha256(a.fixtures.read_bytes()).hexdigest()=='ce63cb4bb69990e44a3a4fbe4e77c24356487617c052debb3ccada1df6dc172c'
assert hashlib.sha256(a.expected.read_bytes()).hexdigest()=='a3c4e7113eb0dc8be16efa0284e5f22827bf5a4ee8bba1afe25a62f9bd167459'
stdin=gzip.decompress(a.fixtures.read_bytes());expected=gzip.decompress(a.expected.read_bytes())
assert len(stdin)==34786*4101 and len(expected)==34786*4122
r=subprocess.run([str(a.executable)],input=stdin,capture_output=True)
assert r.returncode==0,r.stderr.decode(errors='replace')
assert r.stdout==expected,'Retained control RAM/event records differ'
print('PASS34786 retained partial-control records; hardware/helper bodies not executed')
'''

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository',type=Path,default=Path('/home/rs/projects/opencs/ai-line-analysis'))
    parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    root=args.repository.resolve();lib=root/'uc-library'
    if not lib.is_dir():lib=root/'uc-library'
    assert lib.is_dir() and not lib.is_symlink()
    sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
    def checked(relative,digest):
        path=(lib/relative).resolve();assert path.is_relative_to(lib) and path.is_file() and sha(path)==digest,relative
        return path
    for name,digest in BASELINE.items():checked(name,digest)
    led=lib/'candidates/panel-led-control-lifecycle';server=lib/'candidates/uc-file-server-service';raw=lib/'candidates/efm-fader-control-dispatch'
    ledmap=json.loads(checked('candidates/panel-led-control-lifecycle/validation/seal-02/CONTROLLED-APPLY.json','033118d327c1ba6b3b4a0e0a84f459bbbfa48da7fb0b1561bc71cc1fa80eda21').read_text())
    servermap=json.loads(checked('candidates/uc-file-server-service/CONTROLLED-APPLY.json','0e4a1a73835a681cf89da5869ff16b3f3a3ecf9cc7a774a6a52aa37745e1c8bf').read_text())
    handoff=json.loads(checked('candidates/efm-fader-control-dispatch/HANDOFF.json','17c001f40940dc3475691d1eefdc0fe03b45ae88c729050db18abcbe696ae0d9').read_text())
    checked('candidates/panel-led-control-lifecycle/validation/seal-02/validation.json','8c4e84834e476fb9be124f793d7ae5ae612846ebb19b6bd16713850762bb8038')
    checked('candidates/uc-file-server-service/validation/native-02/pending-validation.json','cb0f7a7edb4675ebc1e5d7312e32ae230ee105b0e8590229b9588871d6761ae5')
    checked('candidates/efm-fader-control-dispatch/'+handoff['proof']['path'],handoff['proof']['sha256'])
    for name,digest in handoff['frozen_prior_bindings'].items():checked(name.removeprefix('uc-library/'),digest)
    writes={};previous={};origins={}
    def add(source,target,digest,old=None):
        assert target not in writes and not Path(target).is_absolute() and '..' not in Path(target).parts
        path=checked(source,digest);destination=lib/target;assert not destination.is_symlink()
        if old is None:assert not destination.exists(),target
        else:assert destination.is_file() and sha(destination)==old,target
        writes[target]=path.read_bytes();previous[target]=old;origins[target]={'source':source,'sha256':digest}
    assert len(ledmap['products'])==7 and len(servermap['products'])==3
    for row in ledmap['products']:add(row['source'],row['target'],row['sha256'],row['previous_sha256'])
    for row in servermap['products']:
        assert row['required_destination']=='absent';add(str((server/row['source']).relative_to(lib)),row['destination'],row['sha256'])
    rawproducts=[('include/efm_control_dispatch.hpp','include/presonus/embedded_efm/efm_control_dispatch.hpp'),('src/efm_control_dispatch.cpp','src/embedded_efm/efm_control_dispatch.cpp'),('tests/control_driver.cpp','tests/efm_control_driver.cpp')]
    for source,target in rawproducts:
        rel=str((raw/source).relative_to(lib));add(rel,target,handoff['products']['uc-library/'+rel])
    for source,target,digest in FIXTURES:add(source,target,digest)
    assert len(writes['validation/uc-file-server-service/fixtures.stdin'].splitlines())==13312
    assert len(writes['validation/uc-file-server-service/arm-output.txt'].splitlines())==13312
    assert len(gzip.decompress(writes['validation/embedded-efm/control/fixtures.bin.gz']))==34786*4101
    assert len(gzip.decompress(writes['validation/embedded-efm/control/arm-output.bin.gz']))==34786*4122
    target='tools/embedded_efm_control_replay.py';assert not (lib/target).exists();writes[target]=CONTROL_REPLAY.encode();previous[target]=None;origins[target]={'source':'New fixed-record retained replay helper; existing replay tools unchanged'}
    # Clone phase paths only. Root separately drafts guarded deferred-tally derivatives.
    for name in ('inspect_closure.py','replay_existing.py'):
        old='candidates/noaa-spi-refresh-file-transfer-panel/tools/'+name
        target='candidates/noaa-spi-refresh-led-server-control/tools/'+name
        source=lib/old;assert source.is_file() and not source.is_symlink() and not (lib/target).exists()
        text=source.read_text().replace('noaa-spi-refresh-file-transfer-panel','noaa-spi-refresh-led-server-control').replace('file-transfer-panel-root','led-server-control-root').replace('file-transfer-panel-01','led-server-control-01')
        writes[target]=text.encode();previous[target]=None;origins[target]={'source':old,'source_sha256':sha(source),'adaptation':'Phase paths only; all validation gates retained'}
    groups=(lib/'cmake/ProductionSourceGroups.cmake').read_text();oldgroups=groups
    cmake=(lib/'CMakeLists.txt').read_text();oldcmake=cmake
    def once(text,old,new):assert text.count(old)==1,old;return text.replace(old,new,1)
    def count_sources(text,group):return len(re.search(r'set\(PRESONUS_'+group+r'_SOURCES\n(.*?)\n\)',text,re.S).group(1).split())
    assert [count_sources(groups,x) for x in ('common','cs18','rm')]==[62,24,6]
    groups=once(groups,'set(PRESONUS_common_SOURCES\n','set(PRESONUS_common_SOURCES\n  src/Presonus/Panel/LEDControlLifecycle.cpp\n  src/Presonus/UC/FileServerImplementation.cpp\n')
    groups=once(groups,'set(PRESONUS_cs18_SOURCES\n','set(PRESONUS_cs18_SOURCES\n  src/embedded_efm/efm_control_dispatch.cpp\n')
    groups=once(groups,'set(PRESONUS_PUBLIC_HEADERS\n','set(PRESONUS_PUBLIC_HEADERS\n  presonus/uc/file_server_service.hpp\n  presonus/embedded_efm/efm_control_dispatch.hpp\n')
    assert [count_sources(groups,x) for x in ('common','cs18','rm')]==[64,25,6]
    headers=lambda text:re.findall(r'presonus/[A-Za-z0-9_./]+\.hpp',text)
    assert len(headers(re.search(r'set\(PRESONUS_PUBLIC_HEADERS\n(.*?)\n\)',groups,re.S).group(1)))==80
    cmake=once(cmake,'set(PRESONUS_UC_PUBLIC_HEADERS\n','set(PRESONUS_UC_PUBLIC_HEADERS\n  presonus/embedded_efm/efm_control_dispatch.hpp\n')
    cmake=once(cmake,'  list(APPEND PRESONUS_UC_PUBLIC_HEADERS\n','  list(APPEND PRESONUS_UC_PUBLIC_HEADERS\n    presonus/uc/file_server_service.hpp\n')
    assert len(headers(cmake[cmake.index('set(PRESONUS_UC_PUBLIC_HEADERS'):cmake.index('foreach(header IN LISTS PRESONUS_UC_PUBLIC_HEADERS)')]))==80
    fragment='''  # led-server-control-root: shared host classes and bounded raw MCU control.
  add_executable(panel_led_control_bridge tests/panel_led_control_bridge.cpp tests/panel_led_control_virtual_entry.cpp)
  target_link_libraries(panel_led_control_bridge PRIVATE presonus::uc)
  set_target_properties(panel_led_control_bridge PROPERTIES CXX_EXTENSIONS OFF)
  target_compile_options(panel_led_control_bridge PRIVATE -fno-lto)
  target_link_options(panel_led_control_bridge PRIVATE -fno-lto
'''+''.join('    -Wl,--wrap='+name+'\n' for name in ledmap['wraps'])+'''  )
  add_test(NAME panel_led_control_lifecycle COMMAND panel_led_control_bridge --smoke)
  add_test(NAME panel_led_control_retained COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/panel_led_control_replay.py
    --binary $<TARGET_FILE:panel_led_control_bridge>
    --fixture ${CMAKE_CURRENT_SOURCE_DIR}/validation/panel-led-control-lifecycle/retained/fixtures.jsonl
    --normalization ${CMAKE_CURRENT_SOURCE_DIR}/validation/panel-led-control-lifecycle/retained/getter-normalization.json
    --out-root ${PRESONUS_REPOSITORY_ROOT}/temp/recovery-work/led-control-ctest)
  add_executable(uc_file_server_service_bridge tests/uc_file_server_service_bridge.cpp)
  target_link_libraries(uc_file_server_service_bridge PRIVATE presonus::uc)
  set_target_properties(uc_file_server_service_bridge PROPERTIES CXX_EXTENSIONS OFF)
  target_link_options(uc_file_server_service_bridge PRIVATE -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
  add_test(NAME uc_file_server_service_retained COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/source_port_replay.py
    --executable $<TARGET_FILE:uc_file_server_service_bridge>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-file-server-service/fixtures.stdin
    --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-file-server-service/arm-output.txt --cases 13312)
  add_test(NAME uc_file_server_service_provider COMMAND uc_file_server_service_bridge --provider-smoke)
  set_source_files_properties(src/embedded_efm/efm_control_dispatch.cpp PROPERTIES
    INCLUDE_DIRECTORIES "${CMAKE_CURRENT_SOURCE_DIR}/include/presonus/embedded_efm")
  add_executable(efm_control_driver tests/efm_control_driver.cpp)
  target_include_directories(efm_control_driver PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include/presonus/embedded_efm)
  target_link_libraries(efm_control_driver PRIVATE presonus::cs18_components)
  set_target_properties(efm_control_driver PROPERTIES CXX_EXTENSIONS OFF)
  add_test(NAME embedded_efm_control COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/embedded_efm_control_replay.py
    --executable $<TARGET_FILE:efm_control_driver>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/embedded-efm/control/fixtures.bin.gz
    --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/embedded-efm/control/arm-output.bin.gz)
'''
    cmake=once(cmake,'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)',fragment+'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)')
    # Removing only inserted strings must reconstruct exact prior lists/files.
    assert groups.replace('  src/Presonus/Panel/LEDControlLifecycle.cpp\n  src/Presonus/UC/FileServerImplementation.cpp\n','',1).replace('  src/embedded_efm/efm_control_dispatch.cpp\n','',1).replace('  presonus/uc/file_server_service.hpp\n  presonus/embedded_efm/efm_control_dispatch.hpp\n','',1)==oldgroups
    assert cmake.replace(fragment,'',1).replace('  presonus/embedded_efm/efm_control_dispatch.hpp\n','',1).replace('    presonus/uc/file_server_service.hpp\n','',1)==oldcmake
    for name,data in [('CMakeLists.txt',cmake),('cmake/ProductionSourceGroups.cmake',groups)]:writes[name]=data.encode();previous[name]=BASELINE[name];origins[name]={'source':'Guarded phase-specific additions; exact prior content retained'}
    for name in writes:
        target=(lib/name).resolve();assert target.is_relative_to(lib) and not (lib/name).is_symlink()
    plan={'phase':'led-server-control-root','apply':args.apply,'written_paths':sorted(writes),'production_partitions':[64,25,6],'production_cpp':95,'public_headers':80,'ctest_before':109,'ctest_expected':114,'ledger_expected_after_combined_gate':[603,322,320],'no_admission_in_operator':True,'no_native_oracle_or_build_runs':True,'combined_preflight_required':True,'producer_adjustments':'Root phase-specific LED/NOAA derivatives defer standalone tally only; all component/range/symbol/source guards remain. FileServer --produce-only then --finalize with both fresh ready/pending sets.'}
    print(json.dumps(plan,indent=2),flush=True)
    if not args.apply:return
    phase=root/'evidence/recovery/2026-10-27/led-server-control-root/apply-01';assert not phase.exists();phase.mkdir(parents=True)
    stage=root/'temp/recovery-work/led-server-control-staging-01';assert not stage.exists();stage.mkdir(parents=True)
    snapshots=list(BASELINE)+[name for name,old in previous.items() if old is not None and name not in BASELINE]+['validation/ready-functions.json','validation/compiled-functions.json','validation/integration.json','validation/integration-linux.json','validation/formatting.json','SYMBOLS.md']
    for name in snapshots:
        source=lib/name;target=phase/'before'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    for name,data in writes.items():
        path=stage/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    journal={}
    for name,data in writes.items():
        target=lib/name;old=previous[name]
        assert (not target.exists()) if old is None else (target.is_file() and sha(target)==old),name
        target.parent.mkdir(parents=True,exist_ok=True);os.replace(stage/name,target)
        digest=sha(target);assert digest==hashlib.sha256(data).hexdigest()
        journal[name]={'previous_sha256':old,'applied_sha256':digest,**origins[name]}
        (phase/'applied.json').write_text(json.dumps(journal,indent=2)+'\n')
    (phase/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    print('Guarded application complete; root formatting/build114/source proofs/combined gate still REQUIRED',flush=True)

if __name__=='__main__':main()
