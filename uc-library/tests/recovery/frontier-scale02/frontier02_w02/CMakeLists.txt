# Root includes this after adding the production source/header to its owned lists.
add_executable(frontier02_w02_tests driver.cpp)
target_link_libraries(frontier02_w02_tests PRIVATE presonus_uc)
add_test(NAME frontier02_w02_replay COMMAND "${Python3_EXECUTABLE}"
  "${CMAKE_CURRENT_SOURCE_DIR}/replay.py"
  --executable "$<TARGET_FILE:frontier02_w02_tests>"
  --fixtures "${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json")
