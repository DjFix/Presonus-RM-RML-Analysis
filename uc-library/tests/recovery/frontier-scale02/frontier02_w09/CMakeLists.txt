add_executable(frontier02_w09_driver driver.cpp)
target_link_libraries(frontier02_w09_driver PRIVATE presonus::uc)
target_link_options(frontier02_w09_driver PRIVATE "-Wl,--wrap=_ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE")
add_test(NAME frontier02_w09_replay COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/replay.py" "$<TARGET_FILE:frontier02_w09_driver>" "${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json")
