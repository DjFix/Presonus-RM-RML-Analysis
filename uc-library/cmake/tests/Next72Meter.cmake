# Test subtree only; current72 scope.
add_executable(MeterManagerFamilyCanonicalReplay tests/recovery/meter_manager_family/Replay.cpp)
target_compile_features(MeterManagerFamilyCanonicalReplay PRIVATE cxx_std_17)
target_compile_options(MeterManagerFamilyCanonicalReplay PRIVATE -UNDEBUG -Ulinux -O2)
target_link_libraries(MeterManagerFamilyCanonicalReplay PRIVATE presonus::rm_components PresonusCore::Provider presonus_private_glibc29)
add_test(NAME MeterManagerFamilyCanonicalReplay COMMAND "${PRESONUS_REPOSITORY_ROOT}/uc-library/.venv/bin/python" "uc-library/tests/recovery/meter_manager_family/check.py" "--replay" "--executable" "$<TARGET_FILE:MeterManagerFamilyCanonicalReplay>")
set_tests_properties(MeterManagerFamilyCanonicalReplay PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}" RUN_SERIAL TRUE)
