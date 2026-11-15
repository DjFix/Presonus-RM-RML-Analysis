# Future coordinated Component provider batch; actual production SDK TI required.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/MappingInputRoutes.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto -fno-fast-math -ffp-contract=off)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/MappingRadioRoutes.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto -fno-fast-math -ffp-contract=off)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/MappingRadioValidation.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto -fno-fast-math -ffp-contract=off)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/MappingMeterRouting.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto -fno-fast-math -ffp-contract=off)
include(cmake/tests/SurfaceMapping.cmake)
