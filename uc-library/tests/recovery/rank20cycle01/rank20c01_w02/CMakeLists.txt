# Root reviews/activates this directory after adding the production TU once to
# the CS18 OBJECT partition. The driver uses the canonical role archive.
add_executable(rank20c01_w02_replay driver.cpp)
target_link_libraries(rank20c01_w02_replay PRIVATE presonus_cs18_components)
target_compile_features(rank20c01_w02_replay PRIVATE cxx_std_20)
target_compile_options(rank20c01_w02_replay PRIVATE -fno-rtti)
add_test(NAME rank20c01_w02_replay
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/replay.py"
    "$<TARGET_FILE:rank20c01_w02_replay>" "${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json")
