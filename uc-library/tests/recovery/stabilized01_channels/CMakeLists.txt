add_executable(stabilized01_channels driver.cpp)
target_compile_options(stabilized01_channels PRIVATE -fno-rtti)
target_link_libraries(stabilized01_channels PRIVATE presonus_rm_components)
add_test(NAME stabilized01_channels
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/replay.py
  --executable $<TARGET_FILE:stabilized01_channels>
  --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json)
