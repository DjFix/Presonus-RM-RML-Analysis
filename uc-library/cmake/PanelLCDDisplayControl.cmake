set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Panel/LCDDisplayControl.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto -fno-fast-math -ffp-contract=off)
include(cmake/tests/PanelLCDDisplayControl.cmake)
