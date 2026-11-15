# Test-only registration. Keep production source properties outside this directory.
if(BUILD_TESTING)
  include("${CMAKE_CURRENT_SOURCE_DIR}/candidates/rolling200-02-groups-page/revision02/CanonicalIntegration.cmake")
endif()
