add_executable(ranked09_display_replay driver.cpp)
target_link_libraries(ranked09_display_replay PRIVATE presonus::cs18_components)
add_test(NAME ranked09_display_replay COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/replay.py $<TARGET_FILE:ranked09_display_replay> ${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json)
