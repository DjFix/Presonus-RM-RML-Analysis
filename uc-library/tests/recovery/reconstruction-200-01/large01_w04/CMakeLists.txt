add_executable(reconstruction200_large01_w04 driver.cpp)
target_link_libraries(reconstruction200_large01_w04 PRIVATE presonus_cs18_components)
target_compile_options(reconstruction200_large01_w04 PRIVATE -fno-rtti)
add_test(NAME reconstruction200_large01_w04_native_replay
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/replay.py"
  --executable "$<TARGET_FILE:reconstruction200_large01_w04>"
  --fixtures "${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json")
