# Test-only registration. Keep production source properties outside this directory.
if(BUILD_TESTING)
  add_subdirectory(tests/recovery/stabilized01_channels)
  add_subdirectory(tests/recovery/stabilized01_mapping)
  add_subdirectory(tests/recovery/stabilized01_uart)
endif()
