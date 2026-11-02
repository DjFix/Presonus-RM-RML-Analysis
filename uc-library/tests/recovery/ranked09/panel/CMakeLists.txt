add_executable(ranked09_panel_replay driver.cpp)
target_link_libraries(ranked09_panel_replay PRIVATE presonus_rm_components)
add_test(NAME ranked09_panel_replay COMMAND ${Python3_EXECUTABLE}
  ${CMAKE_CURRENT_SOURCE_DIR}/replay.py $<TARGET_FILE:ranked09_panel_replay>
  ${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json)
