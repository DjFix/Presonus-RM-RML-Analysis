set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/LPCProgrammerGeometry.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto)
include(cmake/tests/LPCProgrammerGeometry.cmake)
