add_executable(frontier_scale01_f03_driver driver.cpp)
target_link_libraries(frontier_scale01_f03_driver PRIVATE presonus::uc)
add_test(NAME frontier_scale01_f03_replay
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/replay.py
    --exe $<TARGET_FILE:frontier_scale01_f03_driver>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json)
