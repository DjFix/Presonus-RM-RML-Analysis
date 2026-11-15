# Every new production body belongs to one audited original-role OBJECT partition.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/NetworkListSelection.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Dsp/ControllerSetupProcess.cpp" APPEND PROPERTY COMPILE_OPTIONS -std=c++20 -fno-lto -fno-fast-math -ffp-contract=off)
include(cmake/tests/GraphRanked09.cmake)
