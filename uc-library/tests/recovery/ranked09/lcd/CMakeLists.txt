# Included by Root after selecting the production CS18 source partition.
add_executable(ranked09_lcd_tests driver.cpp)
target_link_libraries(ranked09_lcd_tests PRIVATE presonus::cs18_components)
add_test(NAME ranked09_lcd_replay COMMAND ${Python3_EXECUTABLE}
  ${CMAKE_CURRENT_SOURCE_DIR}/replay.py
  --exe $<TARGET_FILE:ranked09_lcd_tests>
  --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json)
