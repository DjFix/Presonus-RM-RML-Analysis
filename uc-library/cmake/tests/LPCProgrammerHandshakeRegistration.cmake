# Test-only registration. Keep production source properties outside this directory.
if(BUILD_TESTING)
  include(cmake/tests/LPCProgrammerHandshake.cmake)
endif()
