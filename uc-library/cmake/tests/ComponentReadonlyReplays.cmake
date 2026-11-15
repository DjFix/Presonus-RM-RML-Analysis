# Test-only registration. Keep production source properties outside this directory.
if(BUILD_TESTING)
  set(_component_evidence "${PRESONUS_REPOSITORY_ROOT}/evidence/recovery/2026-11-05/rolling200-02")
  rolling200_02_replay_target(storm_mute_default_name_replay
    "${_component_evidence}/storm-mute-isolated01/driver.cpp" presonus::rm_components)
  rolling200_02_replay_target(storm_scene_default_name_replay
    "${_component_evidence}/isolated-storm-scene01/driver.cpp" presonus::rm_components)
  rolling200_02_replay_target(permissions_readonly_replay
    tests/recovery/PermissionsReadonlyReplay.cpp presonus::rm_components)
  foreach(_target IN ITEMS storm_mute_default_name_replay storm_scene_default_name_replay permissions_readonly_replay)
    target_compile_options(${_target} PRIVATE -fno-rtti)
  endforeach()
  add_test(NAME storm_mute_default_name_native_replay COMMAND ${Python3_EXECUTABLE}
    "${_component_evidence}/storm-mute-isolated01/replay.py"
    --exe $<TARGET_FILE:storm_mute_default_name_replay>
    --fixture "${_component_evidence}/storm-mute-isolated01/NATIVE_REPLAY.json")
  add_test(NAME storm_scene_default_name_native_replay COMMAND ${Python3_EXECUTABLE}
    "${_component_evidence}/isolated-storm-scene01/replay.py"
    --executable $<TARGET_FILE:storm_scene_default_name_replay>
    --fixtures "${_component_evidence}/isolated-storm-scene01/FIXTURES.json"
    --out "${CMAKE_CURRENT_BINARY_DIR}/storm-scene-default-name-replay.json")
  add_test(NAME permissions_readonly_native_replay COMMAND permissions_readonly_replay
    "${PRESONUS_REPOSITORY_ROOT}/evidence/recovery/2026-11-05/permissions-readonly01/native-fixture.txt")
  set_tests_properties(storm_mute_default_name_native_replay storm_scene_default_name_native_replay
    permissions_readonly_native_replay PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")
endif()
