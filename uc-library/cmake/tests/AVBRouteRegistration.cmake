# Test-only registration. Keep production source properties outside this directory.
if(BUILD_TESTING)
  add_subdirectory(tests/recovery/large02-avb-route01)
endif()
