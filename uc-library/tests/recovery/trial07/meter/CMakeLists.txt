cmake_minimum_required(VERSION 3.20)
project(graph_trial07_meter_local LANGUAGES CXX)
get_filename_component(REPO "${CMAKE_CURRENT_LIST_DIR}/../../../../.." ABSOLUTE)
set(CORE_BUILD "${REPO}/temp/core-upstream/root-integration-01")
add_executable(graph_trial07_meter_tests
  "${REPO}/uc-library/tests/graph_trial07_meter_tests.cpp"
  "${REPO}/uc-library/src/Presonus/MeterControl.cpp")
target_compile_features(graph_trial07_meter_tests PRIVATE cxx_std_17)
target_compile_definitions(graph_trial07_meter_tests PRIVATE CORE_USE_OPENSSL=1 NDEBUG=1 PRESONUS_HAS_UPSTREAM_CORE=1)
target_compile_options(graph_trial07_meter_tests PRIVATE -fno-lto -fno-rtti -pthread -Ulinux -Wno-multichar)
target_include_directories(graph_trial07_meter_tests PRIVATE "${REPO}/uc-library/include")
target_include_directories(graph_trial07_meter_tests SYSTEM PRIVATE "${CORE_BUILD}/upstream-core/sdk/include/presonus-core-5")
target_link_libraries(graph_trial07_meter_tests PRIVATE
  "${CORE_BUILD}/upstream-core/sdk/lib/libcorelib.a"
  "${CORE_BUILD}/upstream-core/sdk/lib/libpresonus_core_allocator.a"
  /usr/lib/x86_64-linux-gnu/libpng16.so.16 /usr/lib/x86_64-linux-gnu/libz.so.1 /usr/lib/x86_64-linux-gnu/libssl.so /usr/lib/x86_64-linux-gnu/libcrypto.so
  "${REPO}/temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so"
  dl "${CORE_BUILD}/private-glibc29-provider/libpresonus_private_glibc29.a" m pthread)
foreach(SYM
 _ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE
 _ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE
 _ZN4Core8Portable4View6enableEb
 _ZN4Core8Portable7Control6onIdleEv
 _ZN4Core8Portable7Control12paramChangedEPNS0_9ParameterEi)
 target_link_options(graph_trial07_meter_tests PRIVATE "-Wl,--wrap=${SYM}")
endforeach()
enable_testing()
add_test(NAME meter_original_arm_replay COMMAND
 "${REPO}/uc-library/.venv/bin/python" "${CMAKE_CURRENT_LIST_DIR}/replay.py"
 --executable "$<TARGET_FILE:graph_trial07_meter_tests>" --fixtures "${CMAKE_CURRENT_LIST_DIR}/fixtures.json")
