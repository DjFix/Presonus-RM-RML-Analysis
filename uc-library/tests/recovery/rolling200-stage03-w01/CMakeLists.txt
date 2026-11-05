# Root integrates this test-only fragment after canonical source refresh.
add_executable(rolling200_stage03_w01 driver.cpp)
target_link_libraries(rolling200_stage03_w01 PRIVATE presonus_uc)
target_compile_features(rolling200_stage03_w01 PRIVATE cxx_std_20)
foreach(symbol IN ITEMS
  _ZNK4Core8Portable9Component17getParameterByTagEi
  _ZN8Presonus12MappingTable7connectEPKcPN4Core8Portable9ParameterES2_b
  _ZN8Presonus12MappingTable15setControlColorEPKcS2_
  _ZN8Presonus12MappingTable17setControlEnabledEPKcb)
  target_link_options(rolling200_stage03_w01 PRIVATE "LINKER:--wrap=${symbol}")
endforeach()
add_test(NAME rolling200_stage03_w01_native
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/replay.py
    $<TARGET_FILE:rolling200_stage03_w01>
    ${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json)
get_filename_component(stage03_repository_root "${CMAKE_CURRENT_SOURCE_DIR}/../../../.." ABSOLUTE)
set_tests_properties(rolling200_stage03_w01_native PROPERTIES WORKING_DIRECTORY "${stage03_repository_root}")
