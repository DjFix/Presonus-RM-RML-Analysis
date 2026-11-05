import pathlib,subprocess,json,time
ROOT=pathlib.Path.cwd();OUT=ROOT/'temp/recovery-work/ucnet-idle-local';OUT.mkdir(parents=True,exist_ok=True)
flags=['c++','-std=c++17','-O0','-g','-UNDEBUG','-fno-rtti','-Iuc-library/include','-Ithird_party/ccl-framework','-Itemp/core-upstream/root-integration-01/upstream-core/sdk/include/presonus-core-5']
commands=[flags+['-c','uc-library/src/Presonus/NOAA/TCardUCNetHandlerIO.cpp','-o',str(OUT/'handler.o')],flags+['uc-library/tests/recovery/TCardUCNetIdleReplay.cpp',str(OUT/'handler.o'),'-Wl,--start-group','temp/core-upstream/root-integration-01/libpresonus_rm_components.a','temp/core-upstream/root-integration-01/libpresonus_uc.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a','-Wl,--end-group','-Wl,--wrap=clock_gettime','-pthread','-ldl','-lrt','-o',str(OUT/'replay')]]
regression=commands[1].copy();regression[regression.index('uc-library/tests/recovery/TCardUCNetIdleReplay.cpp')]='uc-library/tests/noaa_ucnet_handler_tests.cpp';regression[-1]=str(OUT/'existing-handler-replay');commands.append(regression)
for cmd in commands:print(json.dumps(cmd),flush=True);subprocess.run(cmd,check=True)
(OUT/'compile-commands.json').write_text(json.dumps(commands,indent=2))
