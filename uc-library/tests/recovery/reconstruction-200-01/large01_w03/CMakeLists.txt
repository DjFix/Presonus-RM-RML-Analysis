# Root adds this directory after integrating the common production source.
add_executable(recovery_large01_w03 driver.cpp)
target_link_libraries(recovery_large01_w03 PRIVATE presonus_uc)
target_compile_features(recovery_large01_w03 PRIVATE cxx_std_20)
add_test(NAME recovery_large01_w03
  COMMAND "${PROJECT_SOURCE_DIR}/.venv/bin/python"
    "${CMAKE_CURRENT_SOURCE_DIR}/replay.py"
    --executable "$<TARGET_FILE:recovery_large01_w03>"
    --fixtures "${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json")
