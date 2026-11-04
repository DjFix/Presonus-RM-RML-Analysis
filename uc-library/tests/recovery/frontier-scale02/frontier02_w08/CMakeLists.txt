add_executable(frontier02_w08_tests driver.cpp)
target_link_libraries(frontier02_w08_tests PRIVATE presonus_cs18_components)
add_test(NAME frontier02_w08_replay COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/replay.py" "$<TARGET_FILE:frontier02_w08_tests>" "${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json")
