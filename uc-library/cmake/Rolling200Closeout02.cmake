# Current-cycle replays link the canonical role archives, never duplicate CPPs.
if(BUILD_TESTING)
  set(_closeout02_evidence "${PRESONUS_REPOSITORY_ROOT}/evidence/recovery/2026-11-05/rolling200-02")

  rolling200_02_replay_target(link_control_draw_native_replay
    candidates/rolling200_02_impl_w02_06/replay.cpp presonus::cs18_components)
  target_compile_options(link_control_draw_native_replay PRIVATE -fno-rtti)
  add_test(NAME link_control_draw_native_replay COMMAND link_control_draw_native_replay
    "${_closeout02_evidence}/stage04-w03/fixtures.txt")

  rolling200_02_replay_target(rolling200_02_pan_drawing_tests
    tests/recovery/rolling200-02/pan-drawing/driver.cpp presonus::cs18_components)
  target_compile_options(rolling200_02_pan_drawing_tests PRIVATE -fno-rtti)
  add_test(NAME rolling200_02_pan_drawing_replay COMMAND ${Python3_EXECUTABLE}
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/recovery/rolling200-02/pan-drawing/check.py"
    replay $<TARGET_FILE:rolling200_02_pan_drawing_tests>
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/recovery/rolling200-02/pan-drawing/fixtures.json")
  set_tests_properties(rolling200_02_pan_drawing_replay PROPERTIES
    WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")

  # Test-only captures resolve serial/provider boundaries; no device I/O occurs.
  rolling200_02_replay_target(noaa_programmer_update_bounded_replay
    candidates/rolling200_02_programmer_resume_w01/replay.cpp presonus::rm_components)
  foreach(_fixture IN ITEMS native epoch-audit)
    add_test(NAME noaa_programmer_update_${_fixture}_replay COMMAND ${Python3_EXECUTABLE}
      "${CMAKE_CURRENT_SOURCE_DIR}/candidates/rolling200_02_programmer_resume_w01/replay.py"
      $<TARGET_FILE:noaa_programmer_update_bounded_replay>
      "${_closeout02_evidence}/programmer-resume-w01/${_fixture}.json")
    set_tests_properties(noaa_programmer_update_${_fixture}_replay PROPERTIES
      WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")
  endforeach()

  rolling200_02_replay_target(permissions_storm_component_replay
    tests/recovery/PermissionsComponentReplay.cpp presonus::rm_components)
  target_compile_options(permissions_storm_component_replay PRIVATE -fno-rtti)
  target_link_options(permissions_storm_component_replay PRIVATE "LINKER:--wrap=clock_gettime")
  add_test(NAME permissions_storm_native_replay COMMAND ${Python3_EXECUTABLE}
    "${CMAKE_CURRENT_SOURCE_DIR}/candidates/rolling200_02_closeout09_owner01/check.py"
    replay $<TARGET_FILE:permissions_storm_component_replay>)
  add_test(NAME permissions_selected_filename_existing_replay COMMAND ${Python3_EXECUTABLE}
    "${CMAKE_CURRENT_SOURCE_DIR}/candidates/rolling200_02_closeout09_owner01/check.py"
    replay_helpers $<TARGET_FILE:permissions_storm_component_replay>)
  set_tests_properties(permissions_storm_native_replay permissions_selected_filename_existing_replay
    PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")
endif()
