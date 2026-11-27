# Test-only registration. Keep production source properties outside this directory.
if(BUILD_TESTING)
  add_library(panel_hal_core_rtti OBJECT
    "${PRESONUS_REPOSITORY_ROOT}/third_party/ccl-framework/core/portable/coreparams.cpp"
    "${PRESONUS_REPOSITORY_ROOT}/third_party/ccl-framework/core/portable/coreattributes.cpp"
    "${PRESONUS_REPOSITORY_ROOT}/third_party/ccl-framework/core/platform/shared/posix/coreatomicstack.posix.cpp"
  )
  target_link_libraries(panel_hal_core_rtti PRIVATE PresonusCore::Provider)
  target_compile_options(panel_hal_core_rtti PRIVATE -frtti -fno-lto)
  target_compile_features(panel_hal_core_rtti PRIVATE cxx_std_17)
  file(MAKE_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}/temp/test-work/panel-motorized_fader")
  configure_file("${CMAKE_CURRENT_SOURCE_DIR}/validation/panel-motorized_fader/fixtures.txt" "${PRESONUS_REPOSITORY_ROOT}/temp/test-work/panel-motorized_fader/fixtures.txt" COPYONLY)
  add_executable(panel_motorized_fader_tests tests/panel_motorized_fader_tests.cpp $<TARGET_OBJECTS:panel_hal_core_rtti>)
  target_compile_options(panel_motorized_fader_tests PRIVATE -frtti -fno-lto -UNDEBUG)
  target_link_options(panel_motorized_fader_tests PRIVATE -fno-lto -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
  target_link_libraries(panel_motorized_fader_tests PRIVATE presonus::uc)
  add_test(NAME panel_motorized_fader_tests COMMAND panel_motorized_fader_tests "${PRESONUS_REPOSITORY_ROOT}/temp/test-work/panel-motorized_fader/fixtures.txt")
  set_tests_properties(panel_motorized_fader_tests PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}/temp/test-work/panel-motorized_fader")
  file(MAKE_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}/temp/test-work/panel-encoder_control")
  configure_file("${CMAKE_CURRENT_SOURCE_DIR}/validation/panel-encoder_control/fixtures.txt" "${PRESONUS_REPOSITORY_ROOT}/temp/test-work/panel-encoder_control/fixtures.txt" COPYONLY)
  add_executable(panel_encoder_control_tests tests/panel_encoder_control_tests.cpp $<TARGET_OBJECTS:panel_hal_core_rtti>)
  target_compile_options(panel_encoder_control_tests PRIVATE -frtti -fno-lto -UNDEBUG)
  target_link_options(panel_encoder_control_tests PRIVATE -fno-lto -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm -Wl,--wrap=_ZN8Presonus5Panel7ControlD2Ev -Wl,--wrap=_ZN8Presonus5Panel16ParamEditHandler15handleParamEditEPN4Core8Portable9ParameterE)
  target_link_libraries(panel_encoder_control_tests PRIVATE presonus::uc)
  add_test(NAME panel_encoder_control_tests COMMAND panel_encoder_control_tests "${PRESONUS_REPOSITORY_ROOT}/temp/test-work/panel-encoder_control/fixtures.txt")
  set_tests_properties(panel_encoder_control_tests PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}/temp/test-work/panel-encoder_control")
  file(MAKE_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}/temp/test-work/panel-blink_led")
  configure_file("${CMAKE_CURRENT_SOURCE_DIR}/validation/panel-blink_led/fixtures.txt" "${PRESONUS_REPOSITORY_ROOT}/temp/test-work/panel-blink_led/fixtures.txt" COPYONLY)
  add_executable(panel_blink_led_tests tests/panel_blink_led_tests.cpp $<TARGET_OBJECTS:panel_hal_core_rtti>)
  target_compile_options(panel_blink_led_tests PRIVATE -frtti -fno-lto -UNDEBUG)
  target_link_options(panel_blink_led_tests PRIVATE -fno-lto -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm -Wl,--wrap=_ZN8Presonus5Panel13SwitchControlC2Eiib -Wl,--wrap=_ZN8Presonus5Panel13SwitchControlD2Ev -Wl,--wrap=_ZN8Presonus5Panel10LEDControl12paramChangedEPN4Core8Portable9ParameterEi)
  target_link_libraries(panel_blink_led_tests PRIVATE presonus::uc)
  add_test(NAME panel_blink_led_tests COMMAND panel_blink_led_tests "${PRESONUS_REPOSITORY_ROOT}/temp/test-work/panel-blink_led/fixtures.txt")
  set_tests_properties(panel_blink_led_tests PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}/temp/test-work/panel-blink_led")
  file(MAKE_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}/temp/test-work/panel-input_gpio")
  configure_file("${CMAKE_CURRENT_SOURCE_DIR}/validation/panel-input_gpio/fixtures.txt" "${PRESONUS_REPOSITORY_ROOT}/temp/test-work/panel-input_gpio/fixtures.txt" COPYONLY)
  add_executable(panel_input_gpio_tests tests/panel_input_gpio_tests.cpp $<TARGET_OBJECTS:panel_hal_core_rtti>)
  target_compile_options(panel_input_gpio_tests PRIVATE -frtti -fno-lto -UNDEBUG)
  target_link_options(panel_input_gpio_tests PRIVATE -fno-lto -Wl,--wrap=_ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE)
  target_link_libraries(panel_input_gpio_tests PRIVATE presonus::uc)
  add_test(NAME panel_input_gpio_tests COMMAND panel_input_gpio_tests "${PRESONUS_REPOSITORY_ROOT}/temp/test-work/panel-input_gpio/fixtures.txt")
  set_tests_properties(panel_input_gpio_tests PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}/temp/test-work/panel-input_gpio")
  # Existing implementation audit; actual production archive, no replacement bodies.
  add_executable(scoped_spi_d0_audit tests/recovery/scoped_spi_d0_audit/Replay.cpp)
  target_compile_features(scoped_spi_d0_audit PRIVATE cxx_std_17)
  target_compile_options(scoped_spi_d0_audit PRIVATE -UNDEBUG -Ulinux -fno-rtti -fno-lto)
  target_link_options(scoped_spi_d0_audit PRIVATE -fno-lto
    -Wl,--wrap=_Znwm -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm
    -Wl,--wrap=_ZN8Presonus5Panel7ControlD2Ev)
  target_link_libraries(scoped_spi_d0_audit PRIVATE presonus_rm_components)
  file(SHA256 "${PRESONUS_REPOSITORY_ROOT}/uc-library/tests/recovery/scoped_spi_d0_audit/fixtures.json" _spi_d0_fixture_sha)
  if(NOT _spi_d0_fixture_sha STREQUAL "2c94b28e1835dee3ac3f1b030ce3ff36a15d25d527d75ca8c4fdfc2e625db90b")
    message(FATAL_ERROR "SPI D0 native fixture changed")
  endif()
  add_test(NAME scoped_spi_d0_audit
    COMMAND "${PRESONUS_REPOSITORY_ROOT}/uc-library/.venv/bin/python" -B
      "${PRESONUS_REPOSITORY_ROOT}/uc-library/tests/recovery/scoped_spi_d0_audit/check.py"
      --exe "$<TARGET_FILE:scoped_spi_d0_audit>"
      --fixtures "${PRESONUS_REPOSITORY_ROOT}/uc-library/tests/recovery/scoped_spi_d0_audit/fixtures.json")
  set_tests_properties(scoped_spi_d0_audit PROPERTIES
    WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}" TIMEOUT 120)
endif()
