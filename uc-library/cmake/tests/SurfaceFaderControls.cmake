# Test-only registration. Keep production source properties outside this directory.
if(BUILD_TESTING)
  if(NOT TARGET panel_hal_core_rtti)
    message(FATAL_ERROR "Existing genuine test-only CCL parameter provider required")
  endif()
  set(_fader_work "${PRESONUS_REPOSITORY_ROOT}/temp/test-work/surface-fader-composition07/surface_fader_commands_tests")
  file(MAKE_DIRECTORY "${_fader_work}")
  add_executable(surface_fader_commands_tests tests/surface_fader_commands_tests.cpp $<TARGET_OBJECTS:panel_hal_core_rtti>)
  target_compile_options(surface_fader_commands_tests PRIVATE -frtti -fno-lto -UNDEBUG -fno-fast-math -ffp-contract=off)
  target_link_libraries(surface_fader_commands_tests PRIVATE stdc++ presonus::cs18_components)
  add_test(NAME surface_fader_commands_tests COMMAND surface_fader_commands_tests)
  set_tests_properties(surface_fader_commands_tests PROPERTIES WORKING_DIRECTORY "${_fader_work}")
  set(_fader_work "${PRESONUS_REPOSITORY_ROOT}/temp/test-work/surface-fader-composition07/surface_fader_readout_tests")
  file(MAKE_DIRECTORY "${_fader_work}")
  configure_file("${CMAKE_CURRENT_SOURCE_DIR}/validation/surface-fader-readout/fixtures.txt" "${_fader_work}/fixtures.txt" COPYONLY)
  add_executable(surface_fader_readout_tests tests/surface_fader_readout_tests.cpp $<TARGET_OBJECTS:panel_hal_core_rtti>)
  target_compile_options(surface_fader_readout_tests PRIVATE -frtti -fno-lto -UNDEBUG -fno-fast-math -ffp-contract=off)
  target_link_libraries(surface_fader_readout_tests PRIVATE stdc++ presonus::cs18_components)
  add_test(NAME surface_fader_readout_tests COMMAND surface_fader_readout_tests "${_fader_work}/fixtures.txt")
  set_tests_properties(surface_fader_readout_tests PROPERTIES WORKING_DIRECTORY "${_fader_work}")
  set(_fader_work "${PRESONUS_REPOSITORY_ROOT}/temp/test-work/surface-fader-composition07/surface_fader_parameter_writes_tests")
  file(MAKE_DIRECTORY "${_fader_work}")
  configure_file("${CMAKE_CURRENT_SOURCE_DIR}/validation/surface-fader-parameter-writes/fixtures.txt" "${_fader_work}/fixtures.txt" COPYONLY)
  add_executable(surface_fader_parameter_writes_tests tests/surface_fader_parameter_writes_tests.cpp $<TARGET_OBJECTS:panel_hal_core_rtti>)
  target_compile_options(surface_fader_parameter_writes_tests PRIVATE -frtti -fno-lto -UNDEBUG -fno-fast-math -ffp-contract=off)
  target_link_libraries(surface_fader_parameter_writes_tests PRIVATE stdc++ presonus::cs18_components)
  add_test(NAME surface_fader_parameter_writes_tests COMMAND surface_fader_parameter_writes_tests "${_fader_work}/fixtures.txt")
  set_tests_properties(surface_fader_parameter_writes_tests PROPERTIES WORKING_DIRECTORY "${_fader_work}")
endif()

if(BUILD_TESTING)
  file(MAKE_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}/temp/test-work/cycle21-g06")
  file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/tests/recovery/cycle21_g06_s04/fixtures.json" surface_cycle_fixture_sha)
  if(NOT surface_cycle_fixture_sha STREQUAL "37bbc5364fe5c118351cf79a3cf2ad9417783625560e196d9926a3dff2359161")
    message(FATAL_ERROR "cycle21_g06_s04 fixture hash mismatch")
  endif()
  add_executable(recovery_cycle21_g06_s04 tests/recovery/cycle21_g06_s04/Replay.cpp)
  target_compile_features(recovery_cycle21_g06_s04 PRIVATE cxx_std_17)
  target_compile_options(recovery_cycle21_g06_s04 PRIVATE -UNDEBUG)
  target_link_libraries(recovery_cycle21_g06_s04 PRIVATE presonus::cs18_components)
  target_link_options(recovery_cycle21_g06_s04 PRIVATE -Wl,--wrap=_ZN8Presonus18MackieControlModel11setMidiSinkEPNS_9IMidiSinkEi)
  add_test(NAME recovery_cycle21_g06_s04 COMMAND "${CMAKE_CURRENT_SOURCE_DIR}/.venv/bin/python" -B
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/recovery/cycle21_g06_s04/check.py"
    --exe "$<TARGET_FILE:recovery_cycle21_g06_s04>"
    --object "${CMAKE_BINARY_DIR}/CMakeFiles/presonus_cs18_objects.dir/src/Presonus/Surface/UCMidiOutputAdapter.cpp.o"
    --integration none
    --out "${PRESONUS_REPOSITORY_ROOT}/temp/test-work/cycle21-g06/cycle21_g06_s04.json")
  set_tests_properties(recovery_cycle21_g06_s04 PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")
  file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/tests/recovery/cycle21_g06_s05/fixtures.json" surface_cycle_fixture_sha)
  if(NOT surface_cycle_fixture_sha STREQUAL "4f734491e5d586bf241392640458d36bb2862ee5ae29116329e56c5ba2c8c449")
    message(FATAL_ERROR "cycle21_g06_s05 fixture hash mismatch")
  endif()
  add_executable(recovery_cycle21_g06_s05 tests/recovery/cycle21_g06_s05/Replay.cpp)
  target_compile_features(recovery_cycle21_g06_s05 PRIVATE cxx_std_17)
  target_compile_options(recovery_cycle21_g06_s05 PRIVATE -UNDEBUG)
  target_link_libraries(recovery_cycle21_g06_s05 PRIVATE presonus::cs18_components)
  add_test(NAME recovery_cycle21_g06_s05 COMMAND "${CMAKE_CURRENT_SOURCE_DIR}/.venv/bin/python" -B
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/recovery/cycle21_g06_s05/check.py"
    --exe "$<TARGET_FILE:recovery_cycle21_g06_s05>"
    --object "${CMAKE_BINARY_DIR}/CMakeFiles/presonus_cs18_objects.dir/src/Presonus/Surface/UCMidiInputAdapter.cpp.o"
    --integration none
    --out "${PRESONUS_REPOSITORY_ROOT}/temp/test-work/cycle21-g06/cycle21_g06_s05.json")
  set_tests_properties(recovery_cycle21_g06_s05 PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")
  file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/tests/recovery/cycle21_g06_s06/fixtures.json" surface_cycle_fixture_sha)
  if(NOT surface_cycle_fixture_sha STREQUAL "d2c051037dee93f2b56b1650bca21aac90c834e3c8caf7215487c6f2287dde32")
    message(FATAL_ERROR "cycle21_g06_s06 fixture hash mismatch")
  endif()
  add_executable(recovery_cycle21_g06_s06 tests/recovery/cycle21_g06_s06/Replay.cpp)
  target_compile_features(recovery_cycle21_g06_s06 PRIVATE cxx_std_17)
  target_compile_options(recovery_cycle21_g06_s06 PRIVATE -UNDEBUG -fno-rtti)
  target_link_libraries(recovery_cycle21_g06_s06 PRIVATE presonus::cs18_components)
  add_test(NAME recovery_cycle21_g06_s06 COMMAND "${CMAKE_CURRENT_SOURCE_DIR}/.venv/bin/python" -B
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/recovery/cycle21_g06_s06/check.py"
    --exe "$<TARGET_FILE:recovery_cycle21_g06_s06>"
    --object "${CMAKE_BINARY_DIR}/CMakeFiles/presonus_cs18_objects.dir/src/LPFControl.cpp.o"
    --integration none
    --out "${PRESONUS_REPOSITORY_ROOT}/temp/test-work/cycle21-g06/cycle21_g06_s06.json")
  set_tests_properties(recovery_cycle21_g06_s06 PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")
  file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/tests/recovery/cycle21_g06_s07/fixtures.json" surface_cycle_fixture_sha)
  if(NOT surface_cycle_fixture_sha STREQUAL "eec8f76819ef6254f8f760ed4ebbaad3b8d1e0207f4f2691485b76c9b1c05708")
    message(FATAL_ERROR "cycle21_g06_s07 fixture hash mismatch")
  endif()
  add_executable(recovery_cycle21_g06_s07 tests/recovery/cycle21_g06_s07/Replay.cpp)
  target_compile_features(recovery_cycle21_g06_s07 PRIVATE cxx_std_17)
  target_compile_options(recovery_cycle21_g06_s07 PRIVATE -UNDEBUG -fno-rtti -fno-sized-deallocation)
  target_link_libraries(recovery_cycle21_g06_s07 PRIVATE presonus::cs18_components)
  add_test(NAME recovery_cycle21_g06_s07 COMMAND "${CMAKE_CURRENT_SOURCE_DIR}/.venv/bin/python" -B
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/recovery/cycle21_g06_s07/check.py"
    --exe "$<TARGET_FILE:recovery_cycle21_g06_s07>"
    --object "${CMAKE_BINARY_DIR}/CMakeFiles/presonus_cs18_objects.dir/src/DefaultMeterInterpolator.cpp.o"
    --integration none
    --out "${PRESONUS_REPOSITORY_ROOT}/temp/test-work/cycle21-g06/cycle21_g06_s07.json")
  set_tests_properties(recovery_cycle21_g06_s07 PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")
  file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/tests/recovery/cycle21_g06_s08/fixtures.json" surface_cycle_fixture_sha)
  if(NOT surface_cycle_fixture_sha STREQUAL "7810954ed2031c64d12a200203d04372c4f6f586bc4ee7f13271d33b6e7510f2")
    message(FATAL_ERROR "cycle21_g06_s08 fixture hash mismatch")
  endif()
  add_executable(recovery_cycle21_g06_s08 tests/recovery/cycle21_g06_s08/Replay.cpp)
  target_compile_features(recovery_cycle21_g06_s08 PRIVATE cxx_std_17)
  target_compile_options(recovery_cycle21_g06_s08 PRIVATE -UNDEBUG -fno-rtti -fno-sized-deallocation)
  target_link_libraries(recovery_cycle21_g06_s08 PRIVATE presonus::cs18_components)
  target_link_options(recovery_cycle21_g06_s08 PRIVATE -Wl,--wrap=_ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE)
  add_test(NAME recovery_cycle21_g06_s08 COMMAND "${CMAKE_CURRENT_SOURCE_DIR}/.venv/bin/python" -B
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/recovery/cycle21_g06_s08/check.py"
    --exe "$<TARGET_FILE:recovery_cycle21_g06_s08>"
    --object "${CMAKE_BINARY_DIR}/CMakeFiles/presonus_cs18_objects.dir/src/LPFControl.cpp.o"
    --integration none
    --out "${PRESONUS_REPOSITORY_ROOT}/temp/test-work/cycle21-g06/cycle21_g06_s08.json")
  set_tests_properties(recovery_cycle21_g06_s08 PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")
  file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/tests/recovery/cycle21_g06_s03/fixtures.json" surface_cycle_fixture_sha)
  if(NOT surface_cycle_fixture_sha STREQUAL "95e91c261128f1d5bcc330e9d82007498a641fc3459deeadd04272d768b72273")
    message(FATAL_ERROR "cycle21_g06_s03 fixture hash mismatch")
  endif()
  add_executable(recovery_cycle21_g06_s03 tests/recovery/cycle21_g06_s03/Replay.cpp)
  target_compile_features(recovery_cycle21_g06_s03 PRIVATE cxx_std_17)
  target_compile_options(recovery_cycle21_g06_s03 PRIVATE -UNDEBUG -fno-rtti)
  target_link_libraries(recovery_cycle21_g06_s03 PRIVATE presonus::cs18_components)
  add_test(NAME recovery_cycle21_g06_s03 COMMAND "${CMAKE_CURRENT_SOURCE_DIR}/.venv/bin/python" -B
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/recovery/cycle21_g06_s03/check.py"
    --exe "$<TARGET_FILE:recovery_cycle21_g06_s03>"
    --object "${CMAKE_BINARY_DIR}/CMakeFiles/presonus_cs18_objects.dir/src/Presonus/MeterScaleControl.cpp.o"
    --integration none
    --out "${PRESONUS_REPOSITORY_ROOT}/temp/test-work/cycle21-g06/cycle21_g06_s03.json")
  set_tests_properties(recovery_cycle21_g06_s03 PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")
endif()

if(BUILD_TESTING AND PRESONUS_ENABLE_UPSTREAM_CORE)
  add_executable(sqlite02_midioutput_c1_replay tests/recovery/sqlite02_midioutput_c1/Replay.cpp)
  target_link_libraries(sqlite02_midioutput_c1_replay PRIVATE presonus::cs18_components)
  target_link_options(sqlite02_midioutput_c1_replay PRIVATE -Wl,--wrap=_ZN8Presonus18MackieControlModel11setMidiSinkEPNS_9IMidiSinkEi)
  target_compile_options(sqlite02_midioutput_c1_replay PRIVATE -UNDEBUG -Ulinux)
  file(SHA256 "${PRESONUS_REPOSITORY_ROOT}/uc-library/tests/recovery/sqlite02_midioutput_c1/fixtures.json" _sqlite01_fixture_sha)
  if(NOT _sqlite01_fixture_sha STREQUAL "864cc031cb8d151f53c9bf53001f12346671f076f18077238e39bcfcb949874a")
    message(FATAL_ERROR "Canonical fixture changed: uc-library/tests/recovery/sqlite02_midioutput_c1/fixtures.json")
  endif()
  add_test(NAME sqlite02_midioutput_c1_replay COMMAND "${PRESONUS_REPOSITORY_ROOT}/uc-library/.venv/bin/python" "-B" "uc-library/tests/recovery/sqlite02_midioutput_c1/check.py" "proof" "--exe" "$<TARGET_FILE:sqlite02_midioutput_c1_replay>" "--object" "${CMAKE_BINARY_DIR}/CMakeFiles/presonus_cs18_objects.dir/src/Presonus/Surface/UCMidiOutputAdapter.cpp.o" "--fixture" "uc-library/tests/recovery/sqlite02_midioutput_c1/fixtures.json" "--integration" "temp/core-upstream/root-integration-01/CMakeCache.txt" "--out" "${CMAKE_BINARY_DIR}/sqlite02_midioutput_c1-ctest.json")
  set_tests_properties(sqlite02_midioutput_c1_replay PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")

  add_executable(sqlite02_midioutput_c2_replay tests/recovery/sqlite02_midioutput_c2/Replay.cpp)
  target_link_libraries(sqlite02_midioutput_c2_replay PRIVATE presonus::cs18_components)
  target_link_options(sqlite02_midioutput_c2_replay PRIVATE -Wl,--wrap=_ZN8Presonus18MackieControlModel11setMidiSinkEPNS_9IMidiSinkEi)
  target_compile_definitions(sqlite02_midioutput_c2_replay PRIVATE MIDI_OUTPUT_BASE_VARIANT)
  target_compile_options(sqlite02_midioutput_c2_replay PRIVATE -UNDEBUG -Ulinux)
  file(SHA256 "${PRESONUS_REPOSITORY_ROOT}/uc-library/tests/recovery/sqlite02_midioutput_c2/fixtures.json" _sqlite01_fixture_sha)
  if(NOT _sqlite01_fixture_sha STREQUAL "f1a307c80800ed39f942b58a9104bee78343c8f8a1cd49b27d4adf16c8e24d14")
    message(FATAL_ERROR "Canonical fixture changed: uc-library/tests/recovery/sqlite02_midioutput_c2/fixtures.json")
  endif()
  add_test(NAME sqlite02_midioutput_c2_replay COMMAND "${PRESONUS_REPOSITORY_ROOT}/uc-library/.venv/bin/python" "-B" "uc-library/tests/recovery/sqlite02_midioutput_c2/check.py" "proof" "--exe" "$<TARGET_FILE:sqlite02_midioutput_c2_replay>" "--object" "${CMAKE_BINARY_DIR}/CMakeFiles/presonus_cs18_objects.dir/src/Presonus/Surface/UCMidiOutputAdapter.cpp.o" "--fixture" "uc-library/tests/recovery/sqlite02_midioutput_c2/fixtures.json" "--integration" "temp/core-upstream/root-integration-01/CMakeCache.txt" "--out" "${CMAKE_BINARY_DIR}/sqlite02_midioutput_c2-ctest.json")
  set_tests_properties(sqlite02_midioutput_c2_replay PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")

  add_executable(sqlite02_midioutput_d1_replay tests/recovery/sqlite02_midioutput_d1/Replay.cpp)
  target_link_libraries(sqlite02_midioutput_d1_replay PRIVATE presonus::cs18_components)
  target_link_options(sqlite02_midioutput_d1_replay PRIVATE -Wl,--wrap=_ZN8Presonus18MackieControlModel11setMidiSinkEPNS_9IMidiSinkEi)
  target_compile_definitions(sqlite02_midioutput_d1_replay PRIVATE MIDI_OUTPUT_DESTRUCTOR)
  target_compile_options(sqlite02_midioutput_d1_replay PRIVATE -UNDEBUG -Ulinux)
  file(SHA256 "${PRESONUS_REPOSITORY_ROOT}/uc-library/tests/recovery/sqlite02_midioutput_d1/fixtures.json" _sqlite01_fixture_sha)
  if(NOT _sqlite01_fixture_sha STREQUAL "4d91e77377c017a05dc5fde6141fd78c99a814c56292707970ba10edcc7a53ef")
    message(FATAL_ERROR "Canonical fixture changed: uc-library/tests/recovery/sqlite02_midioutput_d1/fixtures.json")
  endif()
  add_test(NAME sqlite02_midioutput_d1_replay COMMAND "${PRESONUS_REPOSITORY_ROOT}/uc-library/.venv/bin/python" "-B" "uc-library/tests/recovery/sqlite02_midioutput_d1/check.py" "proof" "--exe" "$<TARGET_FILE:sqlite02_midioutput_d1_replay>" "--object" "${CMAKE_BINARY_DIR}/CMakeFiles/presonus_cs18_objects.dir/src/Presonus/Surface/UCMidiOutputAdapter.cpp.o" "--fixture" "uc-library/tests/recovery/sqlite02_midioutput_d1/fixtures.json" "--integration" "temp/core-upstream/root-integration-01/CMakeCache.txt" "--out" "${CMAKE_BINARY_DIR}/sqlite02_midioutput_d1-ctest.json")
  set_tests_properties(sqlite02_midioutput_d1_replay PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")

  add_executable(sqlite02_midioutput_d2_replay tests/recovery/sqlite02_midioutput_d2/Replay.cpp)
  target_link_libraries(sqlite02_midioutput_d2_replay PRIVATE presonus::cs18_components)
  target_link_options(sqlite02_midioutput_d2_replay PRIVATE -Wl,--wrap=_ZN8Presonus18MackieControlModel11setMidiSinkEPNS_9IMidiSinkEi)
  target_compile_definitions(sqlite02_midioutput_d2_replay PRIVATE MIDI_OUTPUT_BASE_VARIANT MIDI_OUTPUT_DESTRUCTOR)
  target_compile_options(sqlite02_midioutput_d2_replay PRIVATE -UNDEBUG -Ulinux)
  file(SHA256 "${PRESONUS_REPOSITORY_ROOT}/uc-library/tests/recovery/sqlite02_midioutput_d2/fixtures.json" _sqlite01_fixture_sha)
  if(NOT _sqlite01_fixture_sha STREQUAL "7010bd6e8673187bf329a2ae40f89db007f8dd73b9e8fd86a331f6e442c2891b")
    message(FATAL_ERROR "Canonical fixture changed: uc-library/tests/recovery/sqlite02_midioutput_d2/fixtures.json")
  endif()
  add_test(NAME sqlite02_midioutput_d2_replay COMMAND "${PRESONUS_REPOSITORY_ROOT}/uc-library/.venv/bin/python" "-B" "uc-library/tests/recovery/sqlite02_midioutput_d2/check.py" "proof" "--exe" "$<TARGET_FILE:sqlite02_midioutput_d2_replay>" "--object" "${CMAKE_BINARY_DIR}/CMakeFiles/presonus_cs18_objects.dir/src/Presonus/Surface/UCMidiOutputAdapter.cpp.o" "--fixture" "uc-library/tests/recovery/sqlite02_midioutput_d2/fixtures.json" "--integration" "temp/core-upstream/root-integration-01/CMakeCache.txt" "--out" "${CMAKE_BINARY_DIR}/sqlite02_midioutput_d2-ctest.json")
  set_tests_properties(sqlite02_midioutput_d2_replay PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")
endif()
