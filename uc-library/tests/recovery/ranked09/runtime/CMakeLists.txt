add_executable(ranked09_runtime_replay driver.cpp)
target_link_libraries(ranked09_runtime_replay PRIVATE presonus_uc)
# Root must bind the actual production archive facade and canonical Python.
add_test(NAME ranked09_runtime_replay COMMAND ${Python3_EXECUTABLE}
  ${CMAKE_CURRENT_SOURCE_DIR}/replay.py --executable $<TARGET_FILE:ranked09_runtime_replay>
  --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json)
