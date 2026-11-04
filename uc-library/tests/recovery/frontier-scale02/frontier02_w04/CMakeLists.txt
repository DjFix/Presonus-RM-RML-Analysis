add_executable(frontier02_w04_replay driver.cpp)
target_link_libraries(frontier02_w04_replay PRIVATE presonus_rm_components)
target_link_options(frontier02_w04_replay PRIVATE -Wl,--wrap=ioctl)
add_test(NAME frontier02_w04_replay COMMAND ${Python3_EXECUTABLE}
  ${CMAKE_CURRENT_SOURCE_DIR}/replay.py $<TARGET_FILE:frontier02_w04_replay>
  ${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json)
