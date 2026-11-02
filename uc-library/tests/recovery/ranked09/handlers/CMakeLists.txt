# Root adds this subdirectory after assigning the production sources once.
add_executable(ranked09_handlers driver.cpp)
target_link_libraries(ranked09_handlers PRIVATE presonus_cs18_components)
target_compile_options(ranked09_handlers PRIVATE -fno-rtti)
add_test(NAME ranked09_handlers_native_replay
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/replay.py"
  "$<TARGET_FILE:ranked09_handlers>" "${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json")
