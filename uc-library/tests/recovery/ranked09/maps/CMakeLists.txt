add_executable(recovery_ranked09_maps driver.cpp)
target_link_libraries(recovery_ranked09_maps PRIVATE presonus::cs18_components)
add_test(NAME recovery_ranked09_maps COMMAND ${Python3_EXECUTABLE}
  ${CMAKE_CURRENT_SOURCE_DIR}/replay.py $<TARGET_FILE:recovery_ranked09_maps>
  ${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json)
