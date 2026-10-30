set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/UARTLedMeterSender.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto -fno-fast-math -ffp-contract=off)
if(BUILD_TESTING)
  add_executable(uart_led_meter_sender_tests tests/uart_led_meter_sender_tests.cpp)
  target_link_libraries(uart_led_meter_sender_tests PRIVATE stdc++ presonus::uc)
  target_compile_options(uart_led_meter_sender_tests PRIVATE -frtti -UNDEBUG -fno-lto)
  add_test(NAME uart_led_meter_sender COMMAND uart_led_meter_sender_tests
    ${CMAKE_CURRENT_SOURCE_DIR}/validation/uart-led-meter-sender/fixtures.txt)
  set_tests_properties(uart_led_meter_sender PROPERTIES PASS_REGULAR_EXPRESSION
    "PASS cases=12288 real_provider_calls=12288 all_four_bytes=true lengths=6,5 all_write_results=true")
endif()
