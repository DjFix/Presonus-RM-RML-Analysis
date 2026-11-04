add_executable(frontier_scale01_f04_replay driver.cpp)
target_link_libraries(frontier_scale01_f04_replay PRIVATE presonus::uc)
add_test(NAME frontier_scale01_f04_native_replay
  COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/replay.py"
    "$<TARGET_FILE:frontier_scale01_f04_replay>"
    "${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json")
set_tests_properties(frontier_scale01_f04_native_replay PROPERTIES
  WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/../../../../..")
