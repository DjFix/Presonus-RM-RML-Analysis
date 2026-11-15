# Test-only registration. Keep production source properties outside this directory.
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
