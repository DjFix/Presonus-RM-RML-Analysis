# Production CPPs belong exclusively to ProductionSourceGroups.cmake.
set_property(SOURCE src/Presonus/Dsp/ControllerInfo.cpp APPEND PROPERTY
  COMPILE_OPTIONS -std=c++20 -fno-fast-math -ffp-contract=off)
if(BUILD_TESTING)
  function(rolling200_replay_target name source)
    add_executable(${name} ${source})
    target_link_libraries(${name} PRIVATE presonus::uc)
    target_compile_features(${name} PRIVATE cxx_std_20)
    target_compile_options(${name} PRIVATE -UNDEBUG -fno-lto -Ulinux)
  endfunction()
  set(_rolling_evidence "${PRESONUS_REPOSITORY_ROOT}/evidence/recovery/2026-11-05")
  set(_rolling_candidates "${CMAKE_CURRENT_SOURCE_DIR}/candidates")

  rolling200_replay_target(panel_element_replay candidates/rolling200_impl_c12/replay.cpp)
  foreach(_case RANGE 1 10)
    if(_case LESS 10)
      set(_suffix "0${_case}")
    else()
      set(_suffix "${_case}")
    endif()
    add_test(NAME panel_element_replay_${_suffix} COMMAND panel_element_replay
      "${_rolling_evidence}/rolling200-implementation01/c12/rolling200_impl_c12_${_suffix}.tsv")
  endforeach()

  rolling200_replay_target(mappable_mixer_replay tests/recovery/mappable_mixer/replay.cpp)
  add_test(NAME mappable_mixer_replay COMMAND mappable_mixer_replay
    "${_rolling_evidence}/rolling200-mappable-mixer/fixtures.txt")

  rolling200_replay_target(sl_channel_base_replay tests/recovery/sl_channel_base/replay.cpp)
  target_compile_options(sl_channel_base_replay PRIVATE -fno-rtti)
  add_test(NAME sl_channel_base_replay COMMAND sl_channel_base_replay
    "${_rolling_evidence}/rolling200-implementation01/c14/fixtures.tsv")

  rolling200_replay_target(shared_memory_comm_replay candidates/rolling200_impl_c24/replay.cpp)
  add_test(NAME shared_memory_comm_replay COMMAND shared_memory_comm_replay
    "${_rolling_candidates}/rolling200_impl_c24/native.txt")

  rolling200_replay_target(preset_cache_info_replay candidates/rolling200_impl_c17/replay.cpp)
  add_test(NAME preset_cache_info_replay COMMAND ${Python3_EXECUTABLE}
    "${_rolling_candidates}/rolling200_impl_c17/check.py" replay
    $<TARGET_FILE:preset_cache_info_replay>)
  set_tests_properties(preset_cache_info_replay PROPERTIES
    WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")

  rolling200_replay_target(recovery_controller_info candidates/rolling200_impl_c08/driver.cpp)
  target_compile_options(recovery_controller_info PRIVATE -fno-fast-math -ffp-contract=off)
  target_link_libraries(recovery_controller_info PRIVATE presonus_private_glibc29)
  add_test(NAME recovery_controller_info COMMAND ${Python3_EXECUTABLE}
    "${_rolling_candidates}/rolling200_impl_c08/checks.py" replay
    $<TARGET_FILE:recovery_controller_info>
    "${_rolling_evidence}/rolling200-implementation01/rolling200_impl_c08/native-fixture.json")
  set_tests_properties(recovery_controller_info PROPERTIES
    WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")

  rolling200_replay_target(messenger_lifecycle_replay candidates/rolling200_impl_c22/replay.cpp)
  target_link_options(messenger_lifecycle_replay PRIVATE -Wl,--wrap=_ZdlPvm)
  add_test(NAME messenger_lifecycle_replay COMMAND ${Python3_EXECUTABLE}
    "${_rolling_candidates}/rolling200_impl_c22/check.py" replay
    $<TARGET_FILE:messenger_lifecycle_replay>)
  set_tests_properties(messenger_lifecycle_replay PROPERTIES
    WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")
  add_subdirectory(tests/recovery/rolling200-controls01)
  # Pinned provider and canonical control implementation are built without RTTI.
  target_compile_options(rolling200_controls01 PRIVATE -fno-rtti)
endif()
