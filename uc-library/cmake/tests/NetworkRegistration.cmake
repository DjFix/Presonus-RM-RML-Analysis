# Test-only registration. Keep production source properties outside this directory.
if(BUILD_TESTING)
  add_subdirectory(tests/recovery/large02_net_dispatcher01)
  add_subdirectory(tests/recovery/large02_net_adapter01)
  add_subdirectory(tests/recovery/large02_net_registrar01)
endif()
