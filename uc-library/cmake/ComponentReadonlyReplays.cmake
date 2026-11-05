# Replays link canonical role archives; production sources compile only once.
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

if(BUILD_TESTING)
  rolling200_02_replay_target(rack_panel_controls_replay
    candidates/rolling200_02_rack_panel/replay.cpp presonus::rm_components)
  # Derived replay object follows the actual CCL-backed Rack provider RTTI policy.
  target_compile_options(rack_panel_controls_replay PRIVATE -fno-rtti)
  target_link_options(rack_panel_controls_replay PRIVATE
    "LINKER:--wrap=clock_gettime"
    "LINKER:--wrap=_ZN8Presonus5Mixer18MixerComponentBase18resetPermissionsPWEv")
  add_test(NAME rack_panel_controls_native_replay COMMAND ${Python3_EXECUTABLE}
    "${CMAKE_CURRENT_SOURCE_DIR}/candidates/rolling200_02_rack_panel/check.py"
    replay $<TARGET_FILE:rack_panel_controls_replay>)
  rolling200_02_replay_target(network_setup_settings_replay
    tests/recovery/NetworkSetupSettingsReplay.cpp presonus::cs18_components)
  target_compile_options(network_setup_settings_replay PRIVATE -fno-rtti)
  add_test(NAME network_setup_settings_native_replay COMMAND ${Python3_EXECUTABLE}
    "${CMAKE_CURRENT_SOURCE_DIR}/candidates/network-setup-settings/replay.py"
    --executable $<TARGET_FILE:network_setup_settings_replay>
    --fixtures "${CMAKE_CURRENT_SOURCE_DIR}/candidates/network-setup-settings/fixtures.json")
  set_tests_properties(rack_panel_controls_native_replay network_setup_settings_native_replay
    PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")
endif()

# Preserve the independently checked binary32 expression staging in EQ curves.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/EQControl.cpp"
  APPEND PROPERTY COMPILE_OPTIONS -ffp-contract=off)
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

if(BUILD_TESTING)
  include("${CMAKE_CURRENT_SOURCE_DIR}/candidates/rolling200-02-groups-page/revision02/CanonicalIntegration.cmake")
endif()
