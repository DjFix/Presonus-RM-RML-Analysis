add_executable(frontier02_w03_replay driver.cpp)
target_link_libraries(frontier02_w03_replay PRIVATE presonus_uc)
add_test(NAME frontier02_w03_replay
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/replay.py
    $<TARGET_FILE:frontier02_w03_replay> ${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json)
set_tests_properties(frontier02_w03_replay PROPERTIES WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}/..)
