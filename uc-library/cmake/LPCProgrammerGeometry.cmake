set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/LPCProgrammerGeometry.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto)
if(BUILD_TESTING)
add_executable(lpc_programmer_geometry_tests tests/lpc_programmer_geometry_tests.cpp)
target_link_libraries(lpc_programmer_geometry_tests PRIVATE stdc++ presonus::uc)
target_compile_options(lpc_programmer_geometry_tests PRIVATE -UNDEBUG -frtti -fno-lto)
add_test(NAME lpc_programmer_geometry COMMAND ${Python3_EXECUTABLE}
  ${CMAKE_CURRENT_SOURCE_DIR}/tools/lpc_programmer_geometry_replay.py
  --executable $<TARGET_FILE:lpc_programmer_geometry_tests>
  --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/lpc-programmer-geometry/fixtures.txt)
endif()
