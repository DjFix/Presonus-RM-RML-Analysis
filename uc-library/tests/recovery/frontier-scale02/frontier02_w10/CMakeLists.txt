add_executable(frontier02_w10 driver.cpp)
target_link_libraries(frontier02_w10 PRIVATE presonus_uc)
target_compile_options(frontier02_w10 PRIVATE -fno-rtti)
add_test(NAME frontier02_w10 COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/replay.py $<TARGET_FILE:frontier02_w10> ${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json)
