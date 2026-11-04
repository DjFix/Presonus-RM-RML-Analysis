add_executable(large02_net_registrar01 driver.cpp)
target_link_libraries(large02_net_registrar01 PRIVATE presonus_uc)
target_compile_features(large02_net_registrar01 PRIVATE cxx_std_20)
add_test(NAME large02_net_registrar01_native_replay
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/replay.py"
  --driver "$<TARGET_FILE:large02_net_registrar01>"
  --fixtures "${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json")
