add_executable(large01_w02_replay driver.cpp)
target_compile_features(large01_w02_replay PRIVATE cxx_std_20)
target_compile_options(large01_w02_replay PRIVATE -fno-rtti)
target_link_libraries(large01_w02_replay PRIVATE presonus_cs18_components)
add_test(NAME large01_w02_replay COMMAND "${Python3_EXECUTABLE}"
  "${CMAKE_CURRENT_SOURCE_DIR}/replay.py" "$<TARGET_FILE:large01_w02_replay>"
  "${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json")
