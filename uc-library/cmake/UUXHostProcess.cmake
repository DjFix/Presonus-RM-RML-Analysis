set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/UUX/FirmwareUpdaterDispatch.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/UUX/FirmwareUpdaterHostProcess.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/UUX/FirmwareUpdaterPaths.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto)
include(cmake/tests/UUXHostProcess.cmake)
