# Next cohort only. Add to existing panel test subsystem, not production CMake.
# Existing RM providers compile once; both public headers already installed.
add_executable(PresetCacheManagerReplay tests/recovery/preset_cache_manager/Replay.cpp)
target_compile_features(PresetCacheManagerReplay PRIVATE cxx_std_17)
target_compile_options(PresetCacheManagerReplay PRIVATE -Ulinux -pthread)
target_compile_definitions(PresetCacheManagerReplay PRIVATE CORE_USE_OPENSSL=1)
target_link_libraries(PresetCacheManagerReplay PRIVATE presonus::rm_components PresonusCore::Provider ${CMAKE_DL_LIBS} rt)
add_test(NAME PresetCacheManagerReplay COMMAND "${PRESONUS_REPOSITORY_ROOT}/uc-library/.venv/bin/python" "uc-library/tests/recovery/preset_cache_manager/canonical_replay.py" --manifest "temp/recovery-work/rolling-c001-20261124/integration-support/next55-runtime-preflight01/MANIFEST.json" --checker "uc-library/tests/recovery/preset_cache_manager/check.py" -- --out "temp/test-work/preset-cache-manager" --phase replay --exe "$<TARGET_FILE:PresetCacheManagerReplay>" --fixtures "uc-library/tests/recovery/preset_cache_manager/fixtures.json")
set_tests_properties(PresetCacheManagerReplay PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}" RUN_SERIAL TRUE)
