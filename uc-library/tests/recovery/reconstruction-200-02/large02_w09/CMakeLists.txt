# Root adds the new production unit once to COMMON; existing common units remain.
add_executable(large02_w09_replay driver.cpp)
target_link_libraries(large02_w09_replay PRIVATE presonus_uc)
target_compile_features(large02_w09_replay PRIVATE cxx_std_17)
target_compile_options(large02_w09_replay PRIVATE -fno-rtti)
target_link_options(large02_w09_replay PRIVATE -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
add_test(NAME large02_w09_replay
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/replay.py"
    --driver "$<TARGET_FILE:large02_w09_replay>"
    --fixture "${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json")
