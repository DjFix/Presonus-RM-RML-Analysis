add_executable(reconstruction200_large01_w01 driver.cpp)
target_link_libraries(reconstruction200_large01_w01 PRIVATE presonus::uc)
add_test(NAME reconstruction200_large01_w01
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/replay.py
    --executable $<TARGET_FILE:reconstruction200_large01_w01>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json)
