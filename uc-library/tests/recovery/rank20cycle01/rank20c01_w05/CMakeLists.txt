# Root adds production CPP to exactly one partition before enabling this test.
add_executable(rank20c01_w05_replay driver.cpp)
target_link_libraries(rank20c01_w05_replay PRIVATE presonus::rm_components)
add_test(NAME rank20c01_w05_replay
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/replay.py
    --executable $<TARGET_FILE:rank20c01_w05_replay>
    --fixture ${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json)
