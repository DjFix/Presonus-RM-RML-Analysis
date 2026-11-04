add_executable(reconstruction_large01_w10 driver.cpp)
target_link_libraries(reconstruction_large01_w10 PRIVATE presonus_uc)
add_test(NAME reconstruction_large01_w10 COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/replay.py $<TARGET_FILE:reconstruction_large01_w10>)
set_tests_properties(reconstruction_large01_w10 PROPERTIES WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}/..")
