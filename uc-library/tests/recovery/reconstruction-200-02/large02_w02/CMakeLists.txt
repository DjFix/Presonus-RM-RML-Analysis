add_executable(reconstruction200_large02_w02 driver.cpp)
target_link_libraries(reconstruction200_large02_w02 PRIVATE presonus_rm_components)
target_compile_options(reconstruction200_large02_w02 PRIVATE -O3 -fno-rtti)
target_compile_definitions(reconstruction200_large02_w02 PRIVATE NDEBUG)
target_link_options(reconstruction200_large02_w02 PRIVATE -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
add_test(NAME reconstruction200_large02_w02_replay
  COMMAND "${CMAKE_SOURCE_DIR}/.venv/bin/python"
    "${CMAKE_CURRENT_SOURCE_DIR}/replay.py"
    --executable "$<TARGET_FILE:reconstruction200_large02_w02>"
    --fixtures "${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json")
