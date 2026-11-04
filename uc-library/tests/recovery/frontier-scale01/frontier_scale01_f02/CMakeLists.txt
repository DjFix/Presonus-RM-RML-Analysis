add_executable(frontier_scale01_f02_tests driver.cpp)
target_compile_features(frontier_scale01_f02_tests PRIVATE cxx_std_20)
target_link_libraries(frontier_scale01_f02_tests PRIVATE presonus_uc)
add_test(NAME frontier_scale01_f02_replay
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/replay.py"
    "$<TARGET_FILE:frontier_scale01_f02_tests>" "${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json")
