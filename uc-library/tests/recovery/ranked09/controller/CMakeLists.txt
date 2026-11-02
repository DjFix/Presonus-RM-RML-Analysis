add_executable(ranked09_controller_driver driver.cpp)
target_link_libraries(ranked09_controller_driver PRIVATE presonus_uc)
add_test(NAME ranked09_controller_replay
  COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/replay.py
    $<TARGET_FILE:ranked09_controller_driver>
    ${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json)
