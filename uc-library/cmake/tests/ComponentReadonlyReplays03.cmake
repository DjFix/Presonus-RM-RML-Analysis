# Test-only registration. Keep production source properties outside this directory.
if(BUILD_TESTING)
  rolling200_02_replay_target(eq_curves_native_replay
    tests/recovery/rolling200-02/eq-curves/driver.cpp presonus::cs18_components)
  target_compile_options(eq_curves_native_replay PRIVATE -fno-rtti -ffp-contract=off)
  target_link_options(eq_curves_native_replay PRIVATE "LINKER:--wrap=clock_gettime")
  foreach(_kind IN ITEMS curves boundaries)
    if(_kind STREQUAL "curves")
      set(_fixture curve-fixtures.json)
    else()
      set(_fixture fixtures.json)
    endif()
    add_test(NAME eq_${_kind}_native_replay COMMAND ${Python3_EXECUTABLE}
      "${CMAKE_CURRENT_SOURCE_DIR}/tests/recovery/rolling200-02/eq-curves/replay_${_kind}.py"
      $<TARGET_FILE:eq_curves_native_replay>
      "${CMAKE_CURRENT_SOURCE_DIR}/tests/recovery/rolling200-02/eq-curves/${_fixture}")
    set_tests_properties(eq_${_kind}_native_replay PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")
  endforeach()
endif()
