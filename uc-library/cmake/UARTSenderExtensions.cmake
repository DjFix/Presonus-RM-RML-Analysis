set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/UARTPowerGainSender.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto -fno-fast-math -ffp-contract=off)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/UARTColorBrightnessSender.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto -fno-fast-math -ffp-contract=off)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/UARTLedStateSender.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto -fno-fast-math -ffp-contract=off)
include(cmake/tests/UARTSenderExtensions.cmake)
