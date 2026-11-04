# Root integrates this directory after accepting the sealed proposal group.
add_executable(recovery_large02_w03 driver.cpp)
target_link_libraries(recovery_large02_w03 PRIVATE presonus_rm_components)
target_compile_features(recovery_large02_w03 PRIVATE cxx_std_20)
target_compile_options(recovery_large02_w03 PRIVATE -O3 -DNDEBUG)
add_test(NAME recovery_large02_w03
 COMMAND "${PROJECT_SOURCE_DIR}/.venv/bin/python"
 "${CMAKE_CURRENT_SOURCE_DIR}/replay.py"
 --executable "$<TARGET_FILE:recovery_large02_w03>"
 --fixtures "${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json")
