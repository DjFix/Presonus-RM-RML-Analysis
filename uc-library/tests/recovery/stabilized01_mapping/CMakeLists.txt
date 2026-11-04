add_executable(stabilized01_mapping driver.cpp)
target_link_libraries(stabilized01_mapping PRIVATE presonus_uc)
target_compile_features(stabilized01_mapping PRIVATE cxx_std_20)
add_test(NAME stabilized01_mapping_native_replay
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/replay.py"
  --driver "$<TARGET_FILE:stabilized01_mapping>"
  --fixtures "${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json")
