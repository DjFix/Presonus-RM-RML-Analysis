set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/PanelRegistrarFaderCommands.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto -fno-fast-math -ffp-contract=off)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/PanelRegistrarFaderReadout.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto -fno-fast-math -ffp-contract=off)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/PanelRegistrarFaderParameterWrites.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto -fno-fast-math -ffp-contract=off)
include(cmake/tests/SurfaceFaderControls.cmake)
