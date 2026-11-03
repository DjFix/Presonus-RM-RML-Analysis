# Root adds the production CPP exactly once to the COMMON OBJECT partition.
add_executable(frontier01_w03_replay driver.cpp)
target_link_libraries(frontier01_w03_replay PRIVATE presonus_uc)
target_compile_features(frontier01_w03_replay PRIVATE cxx_std_20)
target_compile_options(frontier01_w03_replay PRIVATE -fno-rtti)
add_test(NAME frontier01_w03_replay
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/replay.py"
    --executable "$<TARGET_FILE:frontier01_w03_replay>"
    --fixtures "${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json")
