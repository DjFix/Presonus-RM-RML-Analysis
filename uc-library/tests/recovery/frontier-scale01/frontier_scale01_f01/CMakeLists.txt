add_executable(frontier_scale01_f01 driver.cpp)
target_link_libraries(frontier_scale01_f01 PRIVATE presonus::uc)
add_test(NAME frontier_scale01_f01 COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/replay.py $<TARGET_FILE:frontier_scale01_f01> ${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json)
