set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/UARTMessageSender.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto -fno-fast-math -ffp-contract=off)
if(BUILD_TESTING)
  add_executable(uart_message_sender_tests tests/uart_message_sender_tests.cpp)
  target_link_libraries(uart_message_sender_tests PRIVATE stdc++ presonus::uc)
  target_compile_options(uart_message_sender_tests PRIVATE -frtti -UNDEBUG -fno-lto)
  add_test(NAME uart_message_sender COMMAND uart_message_sender_tests
    ${CMAKE_CURRENT_SOURCE_DIR}/validation/uart-message-sender/fixtures.txt)
  set_tests_properties(uart_message_sender PROPERTIES PASS_REGULAR_EXPRESSION
    "PASS cases=8192 real_provider_calls=8192 initialized_prefix_only=true lengths=6,5 all_write_results=true")
endif()
