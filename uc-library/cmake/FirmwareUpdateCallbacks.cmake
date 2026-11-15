# Future dedicated Component RTTI batch only. No Core source patches.
foreach(_source IN ITEMS src/Presonus/Surface/FirmwareUpdateCallbacks.cpp src/Presonus/Mixer/FirmwareUpdateCallbacks.cpp src/common/FirmwareCallbackText.cpp)
 set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/${_source}" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto)
endforeach()
include(cmake/tests/FirmwareUpdateCallbacks.cmake)
