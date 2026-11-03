# Root adds the production CPP exactly once to the CS18 OBJECT partition.
add_executable(frontier01_w04_replay driver.cpp)
target_compile_features(frontier01_w04_replay PRIVATE cxx_std_20)
target_compile_options(frontier01_w04_replay PRIVATE -fno-rtti)
target_link_libraries(frontier01_w04_replay PRIVATE presonus_cs18_components)
add_test(NAME frontier01_w04_replay
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/replay.py"
    "$<TARGET_FILE:frontier01_w04_replay>" "${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json")
