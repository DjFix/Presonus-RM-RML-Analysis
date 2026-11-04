# Root integrates production CPP exactly once in RM object partition.
add_executable(frontier02_w05_replay_driver driver.cpp)
target_link_libraries(frontier02_w05_replay_driver PRIVATE presonus_rm_components)
add_test(NAME frontier02_w05_native COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/oracle.py)
set_tests_properties(frontier02_w05_native PROPERTIES WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}/..)
add_test(NAME frontier02_w05_replay COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/replay.py --executable $<TARGET_FILE:frontier02_w05_replay_driver> --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json)
