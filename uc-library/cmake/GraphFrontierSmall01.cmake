# Bounded app source ports; exact role ownership is retained in trial evidence.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/frontier01/frontier01_w01.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/frontier01/frontier01_w02.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/frontier01/frontier01_w03.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/frontier01/frontier01_w04.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-rtti)
if(BUILD_TESTING)
  add_subdirectory(tests/recovery/frontier-small01/frontier01_w01)
  add_subdirectory(tests/recovery/frontier-small01/frontier01_w02)
  add_subdirectory(tests/recovery/frontier-small01/frontier01_w03)
  add_subdirectory(tests/recovery/frontier-small01/frontier01_w04)
  foreach(target frontier01_w01_replay_driver frontier01_w02_replay_driver frontier01_w03_replay frontier01_w04_replay)
    target_compile_options(${target} PRIVATE -UNDEBUG -fno-lto -Ulinux)
  endforeach()
  target_compile_options(frontier01_w01_replay_driver PRIVATE -fno-rtti)
  file(MAKE_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/../temp/test-work/frontier-small01")
  add_test(NAME frontier01_w03_native COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/recovery/frontier-small01/frontier01_w03/oracle.py"
    --verify "${CMAKE_CURRENT_SOURCE_DIR}/tests/recovery/frontier-small01/frontier01_w03/fixtures.json")
  add_test(NAME frontier01_w04_native COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/recovery/frontier-small01/frontier01_w04/oracle.py"
    "${CMAKE_CURRENT_SOURCE_DIR}/../temp/test-work/frontier-small01/frontier01_w04-native.json"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/recovery/frontier-small01/frontier01_w04/fixtures.json")
  set_tests_properties(frontier01_w03_native frontier01_w04_native
    PROPERTIES WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/..")
endif()
