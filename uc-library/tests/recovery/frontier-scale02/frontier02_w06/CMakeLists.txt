add_executable(frontier02_w06_replay driver.cpp)
target_link_libraries(frontier02_w06_replay PRIVATE presonus_rm_components)
add_test(NAME frontier02_w06_native_provider_replay
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/replay.py"
  --executable "$<TARGET_FILE:frontier02_w06_replay>"
  --fixtures "${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json")
set_tests_properties(frontier02_w06_native_provider_replay PROPERTIES
  WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/../../../../..")
