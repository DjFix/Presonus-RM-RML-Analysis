add_executable(reconstruction200_large01_w05 driver.cpp)
target_link_libraries(reconstruction200_large01_w05 PRIVATE presonus_uc)
add_test(NAME reconstruction200_large01_w05
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/replay.py
    --executable $<TARGET_FILE:reconstruction200_large01_w05>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json)
