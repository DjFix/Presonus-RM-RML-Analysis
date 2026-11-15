# Production CPPs belong exclusively to ProductionSourceGroups.cmake.
set_property(SOURCE src/Presonus/Dsp/ControllerInfo.cpp APPEND PROPERTY
  COMPILE_OPTIONS -std=c++20 -fno-fast-math -ffp-contract=off)
include(cmake/tests/Rolling200Implementation01.cmake)
