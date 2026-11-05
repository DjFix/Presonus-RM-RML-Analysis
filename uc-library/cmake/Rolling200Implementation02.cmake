# Production CPPs must occur once in ProductionSourceGroups.cmake.
if(BUILD_TESTING)
  function(rolling200_02_replay_target name source role)
    add_executable(${name} ${source})
    target_link_libraries(${name} PRIVATE ${role})
    target_compile_features(${name} PRIVATE cxx_std_17)
    target_compile_options(${name} PRIVATE -UNDEBUG -fno-lto -Ulinux)
  endfunction()
  set(_rolling200_02_evidence "${PRESONUS_REPOSITORY_ROOT}/evidence/recovery/2026-11-05/rolling200-02")

  rolling200_02_replay_target(noaa_tcard_purge_events_replay
    candidates/rolling200-02-tcard-events/replay.cpp presonus::rm_components)
  target_compile_options(noaa_tcard_purge_events_replay PRIVATE -fno-rtti)
  target_link_options(noaa_tcard_purge_events_replay PRIVATE -Wl,--wrap=usleep)
  add_test(NAME noaa_tcard_purge_events_replay COMMAND noaa_tcard_purge_events_replay
    "${_rolling200_02_evidence}/tcard-events/fixture.txt")

  rolling200_02_replay_target(presonus_rolling200_02_stage03_w04_replay
    candidates/rolling200_02_stage03_w04/replay.cpp presonus::uc)
  target_compile_options(presonus_rolling200_02_stage03_w04_replay PRIVATE
    -fno-rtti -fno-fast-math -ffp-contract=off)
  target_link_options(presonus_rolling200_02_stage03_w04_replay PRIVATE
    -Wl,--wrap=_ZN8presonus4dice19packetClockRawTicksEv
    -Wl,--wrap=_ZN4Core8Portable14ViewAttributes9getBitmapERKNS0_10AttributesEPKc)
  add_test(NAME presonus_rolling200_02_stage03_w04_replay
    COMMAND presonus_rolling200_02_stage03_w04_replay)

  rolling200_02_replay_target(avb_noaa_receive_replay
    candidates/rolling200_02_impl_w02_05/receive_tests.cpp presonus::uc)
  target_link_libraries(avb_noaa_receive_replay PRIVATE ZLIB::ZLIB)
  target_link_options(avb_noaa_receive_replay PRIVATE
    -Wl,--wrap=_ZN8Presonus3AVB14AvbManagerBase15unpackAvbSpiMsgEPhPKhi
    -Wl,--wrap=_ZN8Presonus3AVB11AvbListener6updateEhhh
    -Wl,--wrap=_ZN8Presonus3AVB9AvbTalker6updateEhh)
  add_test(NAME avb_noaa_receive_replay COMMAND avb_noaa_receive_replay
    "${_rolling200_02_evidence}/rolling200_02_impl_w02_05/native02/receive-vectors.txt.gz")

  add_subdirectory(tests/recovery/rolling200-stage03-w01)
  target_compile_options(rolling200_stage03_w01 PRIVATE
    -UNDEBUG -fno-rtti -fno-lto -Ulinux)

  rolling200_02_replay_target(noaa_fpga_updater_bounded_replay
    candidates/rolling200_02_stage03_w06/replay.cpp presonus::rm_components)
  add_test(NAME noaa_fpga_updater_bounded_replay COMMAND noaa_fpga_updater_bounded_replay
    "${_rolling200_02_evidence}/updater02/fixtures.txt")
  rolling200_02_replay_target(rolling200_02_eq_control_tests
    tests/recovery/rolling200-02/eq-control/driver.cpp presonus::cs18_components)
  target_compile_options(rolling200_02_eq_control_tests PRIVATE -fno-rtti)
  add_test(NAME rolling200_02_eq_control_replay COMMAND ${Python3_EXECUTABLE}
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/recovery/rolling200-02/eq-control/check.py"
    replay $<TARGET_FILE:rolling200_02_eq_control_tests>
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/recovery/rolling200-02/eq-control/fixtures.json")
  set_tests_properties(rolling200_02_eq_control_replay PROPERTIES
    WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")
endif()
