# Production CPP belongs exactly once in the RM OBJECT partition; Root owns it.
add_executable(frontier01_w02_replay_driver driver.cpp)
target_link_libraries(frontier01_w02_replay_driver PRIVATE presonus_rm_components)
add_test(NAME frontier01_w02_native COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/oracle.py)
set_tests_properties(frontier01_w02_native PROPERTIES WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}/..)
add_test(NAME frontier01_w02_replay COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/replay.py --executable $<TARGET_FILE:frontier01_w02_replay_driver> --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json)
