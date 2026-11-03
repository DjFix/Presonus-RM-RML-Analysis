add_executable(rank20c01_w04_driver driver.cpp)
target_link_libraries(rank20c01_w04_driver PRIVATE presonus_cs18_components)
add_test(NAME rank20c01_w04_replay
  COMMAND "${CMAKE_SOURCE_DIR}/.venv/bin/python" "${CMAKE_CURRENT_SOURCE_DIR}/replay.py"
    --exe $<TARGET_FILE:rank20c01_w04_driver>
    --fixtures "${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json")
