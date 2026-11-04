add_executable(reconstruction200_large01_w08 driver.cpp)
target_link_libraries(reconstruction200_large01_w08 PRIVATE presonus_uc)
# Root integrates source partition first. replay.py additionally executes native oracle.
add_test(NAME reconstruction200_large01_w08 COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/replay.py --executable $<TARGET_FILE:reconstruction200_large01_w08>)
set_tests_properties(reconstruction200_large01_w08 PROPERTIES WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/../../../../..")
