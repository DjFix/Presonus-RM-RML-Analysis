# Common original-scoped feedback logic, no physical power IO in tests.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Panel/PhantomPowerControl.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto -fno-fast-math -ffp-contract=off)
include(cmake/tests/PanelPhantomPower.cmake)
