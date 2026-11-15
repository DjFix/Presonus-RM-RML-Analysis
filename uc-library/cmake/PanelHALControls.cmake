# Original-scoped HAL controls; genuine pinned CCL is the only Core provider.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Panel/MotorizedFaderControl.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto -fno-fast-math -ffp-contract=off)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Panel/EncoderControl.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto -fno-fast-math -ffp-contract=off)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Panel/KeyInputProvider.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto -fno-fast-math -ffp-contract=off)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Panel/BlinkLEDControl.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto -fno-fast-math -ffp-contract=off)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Panel/InputGPIOControl.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto -fno-fast-math -ffp-contract=off)
include(cmake/tests/PanelHALControls.cmake)
