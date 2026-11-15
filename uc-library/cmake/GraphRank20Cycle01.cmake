# Original role ownership and exact common/CS18/RM partition recorded by Root.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/MeterControl.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/MackieControlUnit.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)
include(cmake/tests/GraphRank20Cycle01.cmake)
